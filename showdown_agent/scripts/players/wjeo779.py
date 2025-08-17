from dataclasses import dataclass, field, asdict, replace
from typing import Dict, List, Optional
from poke_env.battle import AbstractBattle
from poke_env.player import Player
from poke_env.battle.side_condition import SideCondition
from poke_env.battle.pokemon import Pokemon
from poke_env.battle.move_category import MoveCategory

# ────────────────────────────────────────────────────────────
#  TEAM  (Iron Head Koraidon + minor EV tweaks for consistency)
# ────────────────────────────────────────────────────────────
team = """
Landorus-Therian @ Rocky Helmet  
Ability: Intimidate  
Tera Type: Fairy  
EVs: 216 HP / 252 Def / 40 Spe  
Impish Nature  
- Earthquake  
- Taunt  
- Stealth Rock  
- U-turn  

Arceus-Water @ Splash Plate  
Ability: Multitype  
Tera Type: Fairy  
EVs: 240 HP / 252 Def / 16 Spe  
Bold Nature  
- Judgment  
- Dragon Tail  
- Thunder Wave  
- Recover  

Eternatus @ Heavy-Duty Boots  
Ability: Pressure  
Tera Type: Dark
EVs: 200 HP / 252 SpD / 56 Spe  
Timid Nature  
IVs: 0 Atk  
- Dynamax Cannon  
- Flamethrower  
- Toxic  
- Recover  

Ho-Oh @ Heavy-Duty Boots  
Ability: Regenerator  
Tera Type: Flying
EVs: 104 HP / 248 Atk / 156 Spe  
Adamant Nature  
- Sacred Fire  
- Brave Bird  
- Substitute  
- Recover  

Koraidon @ Choice Scarf  
Ability: Orichalcum Pulse  
Tera Type: Fire  
EVs: 252 Atk / 4 SpD / 252 Spe  
Jolly Nature  
- Iron Head
- Close Combat  
- U-turn  
- Flare Blitz  

Zacian-Crowned @ Rusted Sword  
Ability: Intrepid Sword  
Tera Type: Steel  
EVs: 252 Atk / 4 SpD / 252 Spe  
Jolly Nature  
- Behemoth Blade  
- Wild Charge  
- Substitute  
- Swords Dance
"""

# ────────────────────────────────────────────────────────────
#  STREAM‑TEE (unchanged)
# ────────────────────────────────────────────────────────────
import sys, io, atexit
log_file = open("print.log", "w", buffering=1, encoding="utf8")
class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams
    def write(self, text):
        for s in self.streams:
            s.write(text)
    def flush(self):
        for s in self.streams:
            s.flush()
sys.stdout = Tee(sys.__stdout__, log_file)
atexit.register(log_file.close)

# ────────────────────────────────────────────────────────────
#  STATE DATACLASSES (unchanged)
# ────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class StatBoosts:
    atk: int = 0
    def_: int = 0
    spa: int = 0
    spd: int = 0
    spe: int = 0
    accuracy: int = 0
    evasion: int = 0

@dataclass(frozen=True)
class PokemonState:
    name: str
    hp_pct: int
    types: List[str]
    status: Optional[str]
    boosts: StatBoosts
    revealed_moves: List[str]
    item: Optional[str]
    tera_type: Optional[str]

@dataclass(frozen=True)
class FieldState:
    weather: Optional[str]
    terrain: Optional[str]
    hazards_my_side: Dict[str, int] = field(default_factory=dict)
    hazards_opp_side: Dict[str, int] = field(default_factory=dict)
    screens_my_side: Dict[str, int] = field(default_factory=dict)
    screens_opp_side: Dict[str, int] = field(default_factory=dict)

@dataclass(frozen=True)
class BattleState:
    turn: int
    speed_advantage: bool
    my_active: PokemonState
    opp_active: PokemonState
    my_team_remaining: int
    opp_team_remaining: int
    field: FieldState
    can_ko_opp: bool
    opp_can_ko_me: bool

# ────────────────────────────────────────────────────────────
#  HELPERS (minor edits only where noted)
# ────────────────────────────────────────────────────────────

def _boost_dict(raw: Dict[str, int]) -> Dict[str, int]:
    return {('def_' if k == 'def' else k): v for k, v in raw.items()}


def build_pokemon_state(mon: Pokemon) -> PokemonState:
    return PokemonState(
        name           = mon.species,
        hp_pct         = int(mon.current_hp_fraction * 100),
        types          = [t.name for t in mon.types],
        status         = mon.status.name if mon.status else None,
        boosts         = StatBoosts(**_boost_dict(mon.boosts)),
        revealed_moves = list(mon.moves.keys()),
        item           = mon.item,
        tera_type      = mon.tera_type.name if mon.tera_type else None,
    )


def _enum_name(singleton_dict):
    return next(iter(singleton_dict)).name if singleton_dict else None


def build_field_state(battle: AbstractBattle) -> FieldState:
    return FieldState(
        weather=_enum_name(battle.weather),
        terrain=_enum_name(battle.fields),
        hazards_my_side = {
            sc.name: lvl
            for sc, lvl in battle.side_conditions.items()
            if sc in {
                SideCondition.STEALTH_ROCK,
                SideCondition.SPIKES,
                SideCondition.TOXIC_SPIKES,
                SideCondition.STICKY_WEB,
            }
        },
        hazards_opp_side = {
            sc.name: lvl
            for sc, lvl in battle.opponent_side_conditions.items()
            if sc in {
                SideCondition.STEALTH_ROCK,
                SideCondition.SPIKES,
                SideCondition.TOXIC_SPIKES,
                SideCondition.STICKY_WEB,
            }
        },
        screens_my_side = {
            sc.name: turns
            for sc, turns in battle.side_conditions.items()
            if sc in {
                SideCondition.REFLECT,
                SideCondition.LIGHT_SCREEN,
                SideCondition.AURORA_VEIL,
            }
        },
        screens_opp_side = {
            sc.name: turns
            for sc, turns in battle.opponent_side_conditions.items()
            if sc in {
                SideCondition.REFLECT,
                SideCondition.LIGHT_SCREEN,
                SideCondition.AURORA_VEIL,
            }
        },
    )


def snapshot(battle: AbstractBattle) -> BattleState:
    me  = battle.active_pokemon
    opp = battle.opponent_active_pokemon
    return BattleState(
        turn = battle.turn,
        speed_advantage = (
            me is not None and opp is not None and
            (me.stats["spe"] or me.base_stats["spe"]) >
            (opp.stats["spe"] or opp.base_stats["spe"])
        ),
        my_active        = build_pokemon_state(me)  if me  else None,
        opp_active       = build_pokemon_state(opp) if opp else None,
        my_team_remaining  = sum(0 if p.fainted else 1 for p in battle.team.values()),
        opp_team_remaining = sum(0 if p.fainted else 1 for p in battle.opponent_team.values()),
        field           = build_field_state(battle),
        can_ko_opp      = False,
        opp_can_ko_me   = False,
    )

# ────────────────────────────────────────────────────────────
#  PLAYER CLASS
# ────────────────────────────────────────────────────────────
class CustomAgent(Player):
    """Smarter heuristics for the Ubers ladder."""

    # ░░ INIT ░░
    def __init__(self, *args, **kwargs):
        super().__init__(team=team, *args, **kwargs)
        self.last_move : str | None = None
        self.rocks_up  = False
        self.lead_sent = False
        self._debug_on = False

    # ░░ LOGGING ░░
    def _dprint(self, *args, **kwargs):
        if self._debug_on:
            print(*args, **kwargs)

    def _log_this(self, battle: AbstractBattle) -> bool:
        fmt = (battle.format or "").lower()
        opp = (battle.opponent_username or "").lower()
        return fmt.endswith("simpleubers") or opp == "simple-uber"

    def _battle_summary(self, battle: AbstractBattle) -> str:
        outcome = "W" if battle.won else "L" if battle.lost else "T"
        return (
            f"[{battle.battle_tag}] "
            f"{self.username} vs {battle.opponent_username} | "
            f"turns={battle.turn} | result={outcome}"
        )

    def _battle_finished_callback(self, battle: AbstractBattle):
        if self._log_this(battle):
            print(self._battle_summary(battle))

    # ░░ BASIC PROPERTY HELPERS ░░
    def _opp_has_priority(self, battle: AbstractBattle, opp: Pokemon) -> bool:
        return any(mv.priority > 0 for mv in opp.moves.values())

    def _safe_stat(self, mon: Pokemon, live_val, key: str) -> int:
        return live_val if live_val is not None else mon.base_stats[key]

    def _effective_speed(self, mon: Pokemon) -> int:
        return self._safe_stat(mon, mon.stats["spe"], "spe")

    def _should_burn_fish(self, me, opp):
        if 'FIRE' in opp.types or 'WATER' in opp.types or 'ROCK' in opp.types:
            return False
        if me.current_hp_fraction < 0.5:
            return False
        return opp.current_hp_fraction > 0.55 and opp.status is None

    # ░░ NEW ➊  — Meteor‑Beam trap detector ░░
    def _opponent_can_meteor_boost(self, battle: AbstractBattle) -> bool:
        opp = battle.opponent_active_pokemon
        if opp.species not in {"eternatus", "nihilego", "celesteela"}:
            return False
        has_mb   = "meteorbeam" in opp.moves or opp.base_stats["spa"] > 150
        herb_maybe = opp.item in {None, "unknown_item", "powerherb"}
        return has_mb and herb_maybe

    # ░░ DAMAGE ESTIMATION ░░
    def _move_damage_estimate(self, mv, atk: Pokemon, dfn: Pokemon) -> float:
        if mv.base_power == 0:
            return 0
        if mv.category == MoveCategory.PHYSICAL:
            atk_stat = self._safe_stat(atk, atk.stats["atk"], "atk")
            def_stat = self._safe_stat(dfn, dfn.stats["def"], "def")
        elif mv.category == MoveCategory.SPECIAL:
            atk_stat = self._safe_stat(atk, atk.stats["spa"], "spa")
            def_stat = self._safe_stat(dfn, dfn.stats["spd"], "spd")
        else:
            return 0
        core = 0.84 * mv.base_power * atk_stat / max(1, def_stat)
        stab = 1.5 if mv.type in atk.types else 1
        type_mod = mv.type.damage_multiplier(
            dfn.type_1, dfn.type_2, type_chart=atk._data.type_chart
        )
        return core * stab * type_mod

    def _best_move_and_ko(self, atk: Pokemon, dfn: Pokemon,
                          battle: AbstractBattle):
        legal = {m.id for m in battle.available_moves} if atk is battle.active_pokemon else None
        best_mv, best_dmg = None, 0
        for mv in atk.moves.values():
            if legal and mv.id not in legal:
                continue
            dmg = self._move_damage_estimate(mv, atk, dfn)
            if dmg > best_dmg:
                best_mv, best_dmg = mv, dmg
        return (best_mv, best_dmg >= dfn.current_hp) if best_mv else (None, False)

    # ░░ DEFENSIVE PIVOT ➌ (HP threshold) ░░
    def _defensive_pivot(self, battle: AbstractBattle) -> Pokemon:
        opp = battle.opponent_active_pokemon
        switches_raw = list(battle.available_switches)
        # filter out the walking corpses 👻
        switches = [m for m in switches_raw if m.current_hp_fraction > 0.30] or switches_raw
        if not switches:
            return battle.active_pokemon

        def worst_hit(mon):
            if not opp.moves:
                return 0
            return max(self._move_damage_estimate(mv, opp, mon)
                       for mv in opp.moves.values())

        lando = next((m for m in switches if m.species == "landorustherian"), None)
        if (lando and lando.current_hp_fraction > 0.30 and
            SideCondition.STEALTH_ROCK not in battle.opponent_side_conditions and
            self._effective_speed(lando) > self._effective_speed(opp)):
            self._dprint("[DEBUG] PIVOT - Landorus to set Rocks")
            return lando

        hooh = next((m for m in switches if m.species == "hooh"), None)
        if hooh and worst_hit(hooh) <= 0.5 * hooh.max_hp:
            self._dprint("[DEBUG] PIVOT - Ho-Oh for Regenerator tank")
            return hooh

        arcw = next((m for m in switches if m.species == "arceuswater"), None)
        if arcw and worst_hit(arcw) <= 0.5 * arcw.max_hp:
            self._dprint("[DEBUG] PIVOT - Arceus-Water defensive tank")
            return arcw

        pivot = max(switches, key=lambda p: p.current_hp_fraction)
        self._dprint("[DEBUG] PIVOT - fallback to", pivot.species)
        return pivot

    # ░░ BREAKER ░░ (unchanged)
    def _breaker_switch(self, battle: AbstractBattle) -> Pokemon:
        opp = battle.opponent_active_pokemon
        order = ["zaciancrowned", "koraidon", "eternatus"]
        for name in order:
            mon = next((m for m in battle.available_switches if m.species == name), None)
            if not mon:
                continue
            best, _ = self._best_move_and_ko(mon, opp, battle)
            if best:
                dmg = self._move_damage_estimate(best, mon, opp)
                if dmg >= 0.55 * opp.max_hp:
                    if name == "koraidon":
                        fairy_alive = any(
                            p.current_hp_fraction > 0.5 and not p.fainted and
                            "FAIRY" in [t.name for t in p.types]
                            for p in battle.opponent_team.values())
                        if fairy_alive:
                            continue
                    self._dprint("[DEBUG] BREAKER - bring in", name)
                    return mon
        fallback = next(m for m in battle.available_switches if m.species == "eternatus")
        self._dprint("[DEBUG] BREAKER - default to Eternatus")
        return fallback

    # ░░ SPECIAL‑MOVE SHORTCUTS ░░ (unchanged)
    def _special_action(self, me: Pokemon, opp: Pokemon, battle: AbstractBattle):
        if (me.species == "landorustherian" and
            not self.rocks_up and
            "stealthrock" in {m.id for m in battle.available_moves}):
            self._dprint("[DEBUG] SPEC - Landorus Stealth Rock")
            return me.moves["stealthrock"]

        if (me.species == "arceuswater" and
            "thunderwave" in {m.id for m in battle.available_moves} and
            self._effective_speed(opp) > 1.2 * self._effective_speed(me)):
            self._dprint("[DEBUG] SPEC - Arc-Water Thunder Wave")
            return me.moves["thunderwave"]

        if (me.species == "hooh" and
            "sacredfire" in {m.id for m in battle.available_moves} and
            self._should_burn_fish(me, opp)):
            self._dprint("[DEBUG] SPEC - Ho-Oh Sacred Fire burn-fish")
            return me.moves["sacredfire"]

        return None

    # ░░ MAIN DECISION LOOP ░░
    def choose_move(self, battle: AbstractBattle):
        self._debug_on = self._log_this(battle)
        state = snapshot(battle)
        if self._debug_on:
            print("[SNAP]", asdict(state))

        if SideCondition.STEALTH_ROCK in battle.opponent_side_conditions:
            self.rocks_up = True

        # force Landorus lead once
        if battle.turn == 0 and not self.lead_sent and battle.available_switches:
            lando = next((p for p in battle.available_switches if p.species == "landorustherian"), None)
            if lando:
                self.lead_sent = True
                self._dprint("[DEBUG] Lead → Landorus-Therian")
                return self.create_order(lando)

        me, opp = battle.active_pokemon, battle.opponent_active_pokemon

        # ➊ Fairy emergency escape for scarf Koraidon lacking Iron Head (legacy replays)
        if (me.species == "koraidon" and
            opp.species in {"arceusfairy", "xerneas"} and
            "ironhead" not in {m.id for m in battle.available_moves}):
            self._dprint("[DEBUG] Fairy emergency escape")
            return self.create_order(self._defensive_pivot(battle))

        # ➋ Bail if Meteor Beam trap likely (esp. Ho‑Oh staying in)
        if self._opponent_can_meteor_boost(battle) and me.species == "hooh":
            self._dprint("[DEBUG] MeteorBeam trap detected – pivot")
            return self.create_order(self._defensive_pivot(battle))

        # --- no legal moves → must switch
        if not battle.available_moves:
            pivot = self._defensive_pivot(battle)
            self._dprint("[DEBUG] Forced pivot - no legal moves →", pivot.species)
            return self.create_order(pivot)

        # check special one‑off actions
        special = self._special_action(me, opp, battle)
        if special:
            if special.id == "stealthrock":
                self.rocks_up = True
            self.last_move = special.id
            self._dprint("[DEBUG] USING SPECIAL MOVE", special.id)
            return self.create_order(special)

        # evaluate damage races
        best, can_ko = self._best_move_and_ko(me, opp, battle)
        opp_can_ko   = self._best_move_and_ko(opp, me, battle)[1]
        faster_raw   = self._effective_speed(me) > self._effective_speed(opp)
        faster       = faster_raw and not self._opp_has_priority(battle, opp)
        free_turn    = opp.must_recharge or opp.preparing

        state = replace(state, can_ko_opp=can_ko, opp_can_ko_me=opp_can_ko)
        if self._debug_on:
            print("[SNAP+]", asdict(state))

        if can_ko and faster:
            return self.create_order(best)
        if opp_can_ko:
            return self.create_order(self._defensive_pivot(battle))
        if free_turn:
            for mv in battle.available_moves:
                if mv.boosts and sum(v for v in mv.boosts.values() if v > 0) >= 2:
                    return self.create_order(mv)

        # choice lock sanity
        if me.item in {"choicescarf", "choiceband", "choicespecs"} and self.last_move:
            locked_id = self.last_move
            if (locked_id in me.moves and
                me.moves[locked_id].id in {m.id for m in battle.available_moves} and
                self._move_damage_estimate(me.moves[locked_id], me, opp) < 0.25 * opp.max_hp):
                self._dprint("[DEBUG] CHOICE-LOCK bailout")
                return self.create_order(self._breaker_switch(battle))

        # default
        if best:
            self.last_move = best.id
            return self.create_order(best)

        # fallbacks
        return (self.create_order(self._defensive_pivot(battle))
                if battle.available_switches else
                self.choose_random_move(battle))
