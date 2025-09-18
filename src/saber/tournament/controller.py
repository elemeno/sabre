"""Tournament orchestration and scheduling utilities."""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

from saber.config_loader import ExploitCfg, ModelCfg, PersonaCfg, TournamentCfg

MatchResultData = Dict[str, object]
RunMatchFn = Callable[["MatchSpec", Path], MatchResultData]


@dataclass(frozen=True)
class MatchSpec:
    """Full specification for a single tournament match."""

    match_id: str
    attacker: ModelCfg
    defender: ModelCfg
    exploit: ExploitCfg
    persona: PersonaCfg
    secret: str
    secret_index: int
    repetition: int
    defender_prompt: str
    turn_limit: int


@dataclass(frozen=True)
class TournamentRunResult:
    """Container for tournament execution artefacts."""

    matches: List[Tuple[MatchSpec, MatchResultData]]
    summary_path: Path
    csv_path: Path
    matches_dir: Path
    aggregates: Dict[str, object]


__all__ = ["MatchSpec", "TournamentController", "TournamentRunResult"]


class TournamentController:
    """Prepare and execute tournament schedules."""

    def __init__(
        self,
        *,
        config: TournamentCfg,
        models: Dict[str, ModelCfg],
        personas: Dict[str, PersonaCfg],
        exploits: Dict[str, ExploitCfg],
        run_match_fn: RunMatchFn,
        seed: int = 42,
    ) -> None:
        self.config = config
        self.models = models
        self.personas = personas
        self.exploits = exploits
        self.run_match_fn = run_match_fn
        self.seed = seed

    # ---------------------------------------------------------------------
    # Schedule generation
    # ---------------------------------------------------------------------
    def build_schedule(self) -> List[MatchSpec]:
        """Build the ordered schedule for the tournament."""

        repetitions = self.config.settings.repetitions
        turn_limit = self.config.settings.max_turns
        attacker_order = list(self.config.models)
        defender_order = list(self.config.models)
        exploit_order = list(self.config.exploits)

        persona_rotation: Dict[str, List[PersonaCfg]] = {}
        persona_index: Dict[str, int] = {}
        secret_rotation: Dict[str, List[Tuple[int, str]]] = {}
        secret_index: Dict[str, int] = {}

        for exploit_name in exploit_order:
            exploit_cfg = self._get_exploit(exploit_name)
            persona_rotation[exploit_name] = self._persona_cycle(exploit_cfg)
            persona_index[exploit_name] = 0
            secret_rotation[exploit_name] = self._secret_cycle(exploit_cfg)
            secret_index[exploit_name] = 0

        schedule: List[MatchSpec] = []
        match_counter = 0
        for repetition in range(repetitions):
            for attacker_name in attacker_order:
                attacker_cfg = self._get_model(attacker_name)
                for defender_name in defender_order:
                    defender_cfg = self._get_model(defender_name)
                    for exploit_name in exploit_order:
                        exploit_cfg = self._get_exploit(exploit_name)
                        persona_cfg = self._next_persona(exploit_name, persona_rotation, persona_index)
                        secret_idx, secret = self._next_secret(exploit_name, secret_rotation, secret_index)
                        defender_prompt = exploit_cfg.defender_setup.replace("{secret}", secret)
                        match_id = self._match_identifier(
                            counter=match_counter,
                            attacker=attacker_cfg.name,
                            defender=defender_cfg.name,
                            exploit=exploit_cfg.name,
                            repetition=repetition,
                            secret_index=secret_idx,
                        )
                        schedule.append(
                            MatchSpec(
                                match_id=match_id,
                                attacker=attacker_cfg,
                                defender=defender_cfg,
                                exploit=exploit_cfg,
                                persona=persona_cfg,
                                secret=secret,
                                secret_index=secret_idx,
                                repetition=repetition,
                                defender_prompt=defender_prompt,
                                turn_limit=turn_limit,
                            )
                        )
                        match_counter += 1
        return schedule

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def run(self, *, output_dir: Path, max_workers: int = 1) -> TournamentRunResult:
        """Execute the schedule and persist summary artefacts."""

        if max_workers != 1:
            raise NotImplementedError("Multi-worker execution is not implemented yet.")

        schedule = self.build_schedule()
        matches_dir = output_dir / "matches"
        matches_dir.mkdir(parents=True, exist_ok=True)

        results: List[Tuple[MatchSpec, MatchResultData]] = []
        for spec in schedule:
            result = self.run_match_fn(spec, matches_dir)
            results.append((spec, result))

        aggregates = self._summarise(results)
        aggregates["matches_dir"] = str(matches_dir)
        aggregates["summary_output"] = str(output_dir)
        summary_path = output_dir / "tournament-summary.json"
        csv_path = output_dir / "summary.csv"
        self._write_summary(summary_path, aggregates)
        self._write_csv(csv_path, results)

        return TournamentRunResult(
            matches=results,
            summary_path=summary_path,
            csv_path=csv_path,
            matches_dir=matches_dir,
            aggregates=aggregates,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_model(self, name: str) -> ModelCfg:
        try:
            return self.models[name]
        except KeyError as exc:  # pragma: no cover - validated earlier
            raise ValueError(f"Model '{name}' is not defined.") from exc

    def _get_exploit(self, name: str) -> ExploitCfg:
        try:
            return self.exploits[name]
        except KeyError as exc:  # pragma: no cover - validated earlier
            raise ValueError(f"Exploit '{name}' is not defined.") from exc

    def _persona_cycle(self, exploit: ExploitCfg) -> List[PersonaCfg]:
        if not exploit.personas:
            raise ValueError(f"Exploit '{exploit.name}' does not define personas.")
        persona_cfgs = [self._get_persona(name) for name in exploit.personas]
        rng = random.Random(f"{self.seed}:persona:{exploit.name}")
        shuffled = persona_cfgs.copy()
        rng.shuffle(shuffled)
        return shuffled

    def _secret_cycle(self, exploit: ExploitCfg) -> List[Tuple[int, str]]:
        if not exploit.secrets:
            raise ValueError(f"Exploit '{exploit.name}' must define secrets.")
        indexed = list(enumerate(exploit.secrets))
        rng = random.Random(f"{self.seed}:secret:{exploit.name}")
        shuffled = indexed.copy()
        rng.shuffle(shuffled)
        return shuffled

    def _get_persona(self, name: str) -> PersonaCfg:
        try:
            return self.personas[name]
        except KeyError as exc:  # pragma: no cover - validated earlier
            raise ValueError(f"Persona '{name}' is not defined.") from exc

    def _next_persona(
        self,
        exploit_name: str,
        rotation: Dict[str, List[PersonaCfg]],
        counters: Dict[str, int],
    ) -> PersonaCfg:
        personas = rotation[exploit_name]
        index = counters[exploit_name]
        counters[exploit_name] = index + 1
        return personas[index % len(personas)]

    def _next_secret(
        self,
        exploit_name: str,
        rotation: Dict[str, List[Tuple[int, str]]],
        counters: Dict[str, int],
    ) -> Tuple[int, str]:
        secrets = rotation[exploit_name]
        index = counters[exploit_name]
        counters[exploit_name] = index + 1
        return secrets[index % len(secrets)]

    def _match_identifier(
        self,
        *,
        counter: int,
        attacker: str,
        defender: str,
        exploit: str,
        repetition: int,
        secret_index: int,
    ) -> str:
        elements = [
            f"{counter:04d}",
            _slug(attacker),
            _slug(defender),
            _slug(exploit),
            f"rep{repetition}",
            f"sec{secret_index}",
        ]
        return "match_" + "_".join(elements)

    def _summarise(self, results: List[Tuple[MatchSpec, MatchResultData]]) -> Dict[str, object]:
        per_combo: Dict[Tuple[str, str, str], Dict[str, float]] = {}
        per_pair: Dict[Tuple[str, str], Dict[str, float]] = {}
        attacker_totals: Dict[str, Dict[str, float]] = {}
        defender_totals: Dict[str, Dict[str, float]] = {}

        for spec, data in results:
            result = data.get("result", {})
            runtime = data.get("runtime", {})
            success = bool(result.get("success", False))
            turns_to_success = runtime.get("turns_to_success")
            key = (spec.attacker.name, spec.defender.name, spec.exploit.name)
            combo_entry = per_combo.setdefault(key, {"success": 0.0, "total": 0.0, "turns_sum": 0.0, "turns_count": 0.0})
            combo_entry["total"] += 1
            if success:
                combo_entry["success"] += 1
                if isinstance(turns_to_success, (int, float)):
                    combo_entry["turns_sum"] += float(turns_to_success)
                    combo_entry["turns_count"] += 1

            pair_key = (spec.attacker.name, spec.defender.name)
            pair_entry = per_pair.setdefault(pair_key, {"success": 0.0, "total": 0.0})
            pair_entry["total"] += 1
            if success:
                pair_entry["success"] += 1

            attacker_entry = attacker_totals.setdefault(spec.attacker.name, {"success": 0.0, "total": 0.0})
            attacker_entry["total"] += 1
            if success:
                attacker_entry["success"] += 1

            defender_entry = defender_totals.setdefault(spec.defender.name, {"success": 0.0, "total": 0.0})
            defender_entry["total"] += 1
            if success:
                defender_entry["success"] += 1

        combo_rows: List[Dict[str, object]] = []
        for (attacker, defender, exploit), stats in sorted(per_combo.items()):
            success_rate = stats["success"] / stats["total"] if stats["total"] else 0.0
            mean_turns = (
                stats["turns_sum"] / stats["turns_count"]
                if stats["turns_count"]
                else None
            )
            combo_rows.append(
                {
                    "attacker": attacker,
                    "defender": defender,
                    "exploit": exploit,
                    "success_rate": success_rate,
                    "mean_turns_to_success": mean_turns,
                }
            )

        matrix: Dict[str, Dict[str, float]] = {}
        for (attacker, defender), stats in per_pair.items():
            success_rate = stats["success"] / stats["total"] if stats["total"] else 0.0
            matrix.setdefault(attacker, {})[defender] = success_rate

        attacker_effectiveness = _rankings(attacker_totals, key_name="model", success_key="success", total_key="total")
        defender_rates = _rankings(defender_totals, key_name="model", success_key="success", total_key="total")
        defender_robustness = []
        for entry in defender_rates:
            prevented = 1.0 - entry["score"]
            defender_robustness.append({"model": entry["model"], "score": prevented, "total": entry["total"]})
        defender_robustness.sort(key=lambda item: item["score"], reverse=True)

        return {
            "tournament": self.config.name,
            "seed": self.seed,
            "total_matches": len(results),
            "per_combo": combo_rows,
            "pair_matrix": matrix,
            "attacker_effectiveness": attacker_effectiveness,
            "defender_robustness": defender_robustness,
        }

    def _write_summary(self, path: Path, payload: Dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    def _write_csv(self, path: Path, results: List[Tuple[MatchSpec, MatchResultData]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "match_id",
            "attacker",
            "defender",
            "exploit",
            "persona",
            "secret_index",
            "repetition",
            "success",
            "confidence",
            "turns",
            "turns_to_success",
            "output_path",
        ]
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for spec, data in results:
                result = data.get("result", {})
                runtime = data.get("runtime", {})
                row = {
                    "match_id": spec.match_id,
                    "attacker": spec.attacker.name,
                    "defender": spec.defender.name,
                    "exploit": spec.exploit.name,
                    "persona": spec.persona.name,
                    "secret_index": spec.secret_index,
                    "repetition": spec.repetition,
                    "success": bool(result.get("success", False)),
                    "confidence": result.get("confidence", 0.0),
                    "turns": runtime.get("turns"),
                    "turns_to_success": runtime.get("turns_to_success"),
                    "output_path": data.get("meta", {}).get("output_path"),
                }
                writer.writerow(row)


def _rankings(
    stats: Dict[str, Dict[str, float]],
    *,
    key_name: str,
    success_key: str,
    total_key: str,
) -> List[Dict[str, object]]:
    rankings: List[Dict[str, object]] = []
    for name, values in stats.items():
        total = values.get(total_key, 0.0)
        success = values.get(success_key, 0.0)
        score = 0.0
        if total:
            score = success / total
        rankings.append({key_name: name, "score": score, "total": total})
    rankings.sort(key=lambda item: item["score"], reverse=True)
    return rankings


def _slug(value: str) -> str:
    return value.lower().replace(" ", "-")
