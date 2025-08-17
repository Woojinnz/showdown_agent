from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from poke_env.battle import AbstractBattle
from poke_env.player import Player
from poke_env.battle.side_condition import SideCondition
from poke_env.battle.pokemon import Pokemon
from poke_env.battle.move_category import MoveCategory

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
- Outrage  
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

# Helper Functions

def build_pokemon_state(mon) -> PokemonState:
    return PokemonState(
        name=mon.species,
        hp_pct=int(mon.current_hp_fraction * 100),
        types=[t.name for t in mon.types],
        status=mon.status.name if mon.status else None,
        boosts=StatBoosts(**mon.boosts),
        revealed_moves=list(mon.moves.keys()),
        item=mon.item,
        tera_type=mon.tera_type.name if mon.tera_type else None,
    )

def build_field_state(battle: AbstractBattle) -> FieldState:
    return FieldState(
        weather=battle.weather.name if battle.weather else None,
        terrain=battle.fields.terrain.name if battle.fields.terrain else None,
        hazards_my_side={
            sc.name: lvl
            for sc, lvl in battle.side_conditions.items()
            if sc in {
                SideCondition.STEALTH_ROCK,
                SideCondition.SPIKES,
                SideCondition.TOXIC_SPIKES,
                SideCondition.STICKY_WEB,
            }
        },
        hazards_opp_side={
            sc.name: lvl
            for sc, lvl in battle.opponent_side_conditions.items()
            if sc in {
                SideCondition.STEALTH_ROCK,
                SideCondition.SPIKES,
                SideCondition.TOXIC_SPIKES,
                SideCondition.STICKY_WEB,
            }
        },
        screens_my_side={
            sc.name: turns
            for sc, turns in battle.side_conditions.items()
            if sc in {
                SideCondition.REFLECT,
                SideCondition.LIGHT_SCREEN,
                SideCondition.AURORA_VEIL,
            }
        },
        screens_opp_side={
            sc.name: turns
            for sc, turns in battle.opponent_side_conditions.items()
            if sc in {
                SideCondition.REFLECT,
                SideCondition.LIGHT_SCREEN,
                SideCondition.AURORA_VEIL,
            }
        },
    )


class CustomAgent(Player):
    def __init__(self, *args, **kwargs):
        super().__init__(team=team, *args, **kwargs)
        self._choice_lock: dict[str, str] = {}

    def _safe_stat(self, mon: Pokemon, live_val, stat_key: str) -> int:
        return live_val if live_val is not None else mon.base_stats[stat_key]
    
    def _effective_speed(self, mon: Pokemon) -> int:
        live = mon.stats["spe"]
        return live if live is not None else mon.base_stats["spe"]

    def _is_choice_locked(self, mon: Pokemon) -> bool:
        return (
            mon.item
            and "choice" in mon.item.lower()
            and mon.species in self._choice_lock
        )

    def _move_damage_estimate(self, move, atk: Pokemon, dfn: Pokemon) -> float:
        if move.base_power == 0:
            return 0.0

        if move.category == MoveCategory.PHYSICAL:
            atk_stat = self._safe_stat(atk, atk.stats["atk"], "atk")
            def_stat = self._safe_stat(dfn, dfn.stats["def"], "def")
        elif move.category == MoveCategory.SPECIAL:
            atk_stat = self._safe_stat(atk, atk.stats["spa"], "spa")
            def_stat = self._safe_stat(dfn, dfn.stats["spd"], "spd")
        else:
            return 0.0

        core = 0.84 * move.base_power * (atk_stat / max(1, def_stat))
        stab = 1.5 if move.type in atk.types else 1.0
        type_mod = move.type.damage_multiplier(
            dfn.type_1, dfn.type_2, type_chart=atk._data.type_chart
        )
        return core * stab * type_mod

    def _best_move_and_ko(self, attacker: Pokemon, defender: Pokemon, battle) -> Tuple[Optional[Any], bool]:
        legal = {m.id for m in battle.available_moves} if attacker is battle.active_pokemon else None

        best_mv, best_dmg = None, 0.0
        for mv in attacker.moves.values():
            if legal is not None and mv.id not in legal:
                continue                      
            dmg = self._move_damage_estimate(mv, attacker, defender)
            if dmg > best_dmg:
                best_dmg, best_mv = dmg, mv

        return (best_mv, best_dmg >= defender.current_hp) if best_mv else (None, False)
    

    def choose_move(self, battle: AbstractBattle):
        if getattr(self, "_printed_turn", None) != battle.turn:
            print(f"=== DEBUG TURN {battle.turn}")
            self._printed_turn = battle.turn

        if battle.force_switch or not battle.available_moves:
            pivot = max(battle.available_switches,
                        key=lambda p: p.current_hp_fraction)
            print("[DEBUG] R-1 – forced switch →", pivot.species)
            return self.create_order(pivot)

        me: Pokemon  = battle.active_pokemon
        opp: Pokemon = battle.opponent_active_pokemon
        
        if me is None or opp is None:
            print("[DEBUG] Active Pokémon unknown – random move")
            return self.choose_random_move(battle)

        best_move, can_ko_opp = self._best_move_and_ko(me, opp, battle)
        _,       opp_can_ko_me = self._best_move_and_ko(opp, me,battle)
        speed_advantage = self._effective_speed(me) > self._effective_speed(opp)
        free_turn_avail = opp.must_recharge or opp.preparing

        print(f"[DEBUG] can_KO_opp={can_ko_opp} | opp_can_KO_me={opp_can_ko_me} | "
              f"speed_adv={speed_advantage} | free_turn={free_turn_avail}")

        locked_move_id = self._choice_lock.get(me.species)
        is_choice_item = me.item and "choice" in me.item.lower()

        if is_choice_item:
            if locked_move_id:
                if locked_move_id in (m.id for m in battle.available_moves):
                    print("[DEBUG] Choice-LOCK active – repeating move:", locked_move_id)
                    move_obj = next(
                        (m for m in battle.available_moves if m.id == locked_move_id), None
                    )
                    if move_obj:
                        return self.create_order(move_obj)
                    print("[DEBUG] Choice-LOCK vanished – picking best available")
                else:
                    if battle.available_switches:
                        pivot = max(battle.available_switches,
                                    key=lambda p: p.current_hp_fraction)
                        print("[DEBUG] Choice-LOCK move disabled – switching to", pivot.species)
                        return self.create_order(pivot)
      
        if (battle.turn == 1
            and me.species == "Ting-Lu"
            and opp.category != MoveCategory.SPECIAL          
            and self._move_damage_estimate(opp.moves.peek(), opp, me) < me.max_hp * 0.40):

            spikes = me.moves.get("spikes")
            if spikes and spikes.id in {m.id for m in battle.available_moves}:
                print("[DEBUG] R-Early – laying Spikes")
                return self.create_order(spikes)

            ruin = me.moves.get("ruination")
            if ruin and ruin.id in {m.id for m in battle.available_moves}:
                print("[DEBUG] R-Early – Ruination chip")
                return self.create_order(ruin)
            
        if (me.species == "Ting-Lu"
            and best_move and best_move.base_power < 80
            and SideCondition.SPIKES in battle.opponent_side_conditions
            and me.moves.get("whirlwind") in battle.available_moves
        ):
            print("[DEBUG] R-Phaze – Whirlwind to rack hazard damage")
            return self.create_order(me.moves["whirlwind"])
            
        if can_ko_opp and speed_advantage and best_move:
            print("[DEBUG] R-3 – use winning KO move:", best_move.id)
            if is_choice_item:
                self._choice_lock[me.species] = best_move.id
            return self.create_order(best_move)

        if opp_can_ko_me and not speed_advantage and battle.available_switches:
            pivot = max(battle.available_switches,
                        key=lambda p: p.current_hp_fraction)
            print("[DEBUG] R-4 – defensive switch to", pivot.species)
            self._choice_lock.pop(me.species, None)
            return self.create_order(pivot)

        if free_turn_avail and not opp_can_ko_me:
            for mv in battle.available_moves:
                if mv.boosts and sum(v for v in mv.boosts.values() if v > 0) >= 2:
                    print("[DEBUG] R-5 – setup with", mv.id)
                    if is_choice_item:
                        self._choice_lock[me.species] = mv.id
                    return self.create_order(mv)
                
        dmeteor = me.moves.get("dracometeor")
        just_meteored = (
            dmeteor is not None and                 
            dmeteor.times_used > 0 and              
            battle.turn == dmeteor.turn_last_used   
        )
        if (
            just_meteored and                     
            me.boosts["spa"] <= -2 and             
            battle.available_switches
        ):
            pivot = max(battle.available_switches,
                        key=lambda p: p.current_hp_fraction)
            print(f"[DEBUG] Meteor drop – pivoting to {pivot.species}")
            return self.create_order(pivot)

        if best_move:
            print("[DEBUG] R-6 – best damage move:", best_move.id)
            if is_choice_item:
                self._choice_lock[me.species] = best_move.id
            return self.create_order(best_move)

        print("[DEBUG] No rule matched – random move")
        return self.choose_random_move(battle)

    
class ForwardCustomAgent(Player):

    def __init__(self, *args, **kwargs):
            super().__init__(team=team, *args, **kwargs)

    def _safe_stat(self, mon: Pokemon, live_val, stat_key: str) -> int:
        return live_val if live_val is not None else mon.base_stats[stat_key]
    
    def _effective_speed(self, mon: Pokemon) -> int:
        live = mon.stats["spe"]
        return live if live is not None else mon.base_stats["spe"]

    def _move_damage_estimate(self, move, atk: Pokemon, dfn: Pokemon) -> float:
        if move.base_power == 0:
            return 0.0

        if move.category == MoveCategory.PHYSICAL:
            atk_stat = self._safe_stat(atk, atk.stats["atk"], "atk")
            def_stat = self._safe_stat(dfn, dfn.stats["def"], "def")
        elif move.category == MoveCategory.SPECIAL:
            atk_stat = self._safe_stat(atk, atk.stats["spa"], "spa")
            def_stat = self._safe_stat(dfn, dfn.stats["spd"], "spd")
        else:
            return 0.0

        core = 0.84 * move.base_power * (atk_stat / max(1, def_stat))
        stab = 1.5 if move.type in atk.types else 1.0
        type_mod = move.type.damage_multiplier(
            dfn.type_1, dfn.type_2, type_chart=atk._data.type_chart
        )
        return core * stab * type_mod

    def _best_move_and_ko(
        self, attacker: Pokemon, defender: Pokemon
    ) -> Tuple[Optional[str], bool]:
        best_id, best_dmg = None, 0.0
        for mv in attacker.moves.values():
            dmg = self._move_damage_estimate(mv, attacker, defender)
            if dmg > best_dmg:
                best_dmg, best_id = dmg, mv.id
        if best_id is None:
            return None, False
        return best_id, best_dmg >= defender.current_hp
    
    def choose_move(self, battle: AbstractBattle):
            
        me, opp = battle.active_pokemon, battle.opponent_active_pokemon

        best_move_id, can_ko_opp = self._best_move_and_ko(me, opp)
        _, opp_can_ko_me = self._best_move_and_ko(opp, me)
        speed_advantage = self._effective_speed(me) > self._effective_speed(opp)
        free_turn_avail = opp.must_recharge or opp.preparing

        if can_ko_opp and speed_advantage and best_move_id:
            return self.create_order(best_move_id)

        if opp_can_ko_me and not speed_advantage and battle.available_switches:
            pivot = max(
                battle.available_switches, key=lambda m: m.current_hp_fraction
            )
            return self.create_order(pivot)

        if free_turn_avail and not opp_can_ko_me:
            for mv in battle.available_moves:
                if mv.boosts and sum(v for v in mv.boosts.values() if v > 0) >= 2:
                    return self.create_order(mv)

        if best_move_id:
            return self.create_order(best_move_id)

        return self.choose_random_move(battle)