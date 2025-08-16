from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from poke_env.battle import AbstractBattle
from poke_env.player import Player
from poke_env.battle.side_condition import SideCondition
from poke_env.battle.pokemon import Pokemon


team = """
Pikachu @ Focus Sash  
Ability: Static  
Tera Type: Electric  
EVs: 8 HP / 248 SpA / 252 Spe  
Timid Nature  
IVs: 0 Atk  
- Thunder Wave  
- Thunder  
- Reflect
- Thunderbolt  
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

    def choose_move(self, battle: AbstractBattle):

        mine = battle.active_pokemon
        opponent = battle.opponent_active_pokemon



        return self.choose_random_move(battle)
    
        
    def _move_damage_estimate(self, move: Any, atk: Pokemon, dfn: Pokemon) -> float:
        if move.base_power == 0:
            return 0            

        if move.category == "physical":
            atk_stat = atk.stats["atk"]
            def_stat = dfn.stats["def"]
        elif move.category == "special":
            atk_stat = atk.stats["spa"]
            def_stat = dfn.stats["spd"]
        else:        
            return 0

        core     = 0.84 * move.base_power * (atk_stat / max(1, def_stat))
        stab     = 1.5 if move.type in atk.types else 1.0
        type_mod = move.type.damage_multiplier(
            dfn.type_1, dfn.type_2, type_chart=atk._data.type_chart
        )

        return core * stab * type_mod

    def _best_move_and_ko(self, attacker: Pokemon, defender: Pokemon) -> Tuple[Optional[str], bool]:
        best_id, best_dmg = None, 0.0
        for mv in attacker.moves.values():
            dmg = self.move_damage_estimate(mv, attacker, defender)
            if dmg > best_dmg:
                best_dmg, best_id = dmg, mv.id

        if best_id is None:
            return None, False

        return best_id, best_dmg >= defender.current_hp
