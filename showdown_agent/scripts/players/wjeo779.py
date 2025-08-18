import os, time
from typing import Dict, Tuple
from collections import defaultdict
from poke_env.data import *
from poke_env.battle import *
from poke_env.player import *
from poke_env.data import GenData

DMG_THRESHOLD = 0.33

team = """
Landorus-Therian @ Rocky Helmet  
Ability: Intimidate  
Tera Type: Water  
EVs: 240 HP / 252 Def / 16 Spe  
Impish Nature  
- Earthquake  
- Rock Tomb  
- Stealth Rock  
- U-turn  

Ho-Oh @ Heavy-Duty Boots  
Ability: Regenerator  
Tera Type: Fairy  
EVs: 240 HP / 252 Def / 16 Spe  
Impish Nature  
- Sacred Fire  
- Brave Bird  
- Whirlwind  
- Recover  

Kyogre @ Heavy-Duty Boots  
Ability: Drizzle  
Tera Type: Ghost  
EVs: 240 HP / 176 Def / 76 SpA / 16 Spe  
Bold Nature  
IVs: 0 Atk  
- Origin Pulse  
- Ice Beam  
- Calm Mind  
- Thunder  

Koraidon @ Heavy-Duty Boots  
Ability: Orichalcum Pulse  
Tera Type: Fire  
EVs: 252 Atk / 4 SpD / 252 Spe  
Jolly Nature  
- Outrage  
- Low Kick  
- Swords Dance  
- Flame Charge  

Arceus @ Leftovers  
Ability: Multitype  
Tera Type: Fire  
EVs: 248 HP / 204 Atk / 56 Spe  
Adamant Nature  
- Extreme Speed  
- Shadow Claw  
- Bulk Up  
- Taunt  

Kingambit @ Air Balloon  
Ability: Supreme Overlord  
Tera Type: Fire  
EVs: 248 HP / 252 Atk / 8 SpD  
Adamant Nature  
- Kowtow Cleave  
- Iron Head  
- Swords Dance  
- Sucker Punch  

"""

class CustomAgent(Player):
    def __init__(self, **kwargs):
        super().__init__(team=team, **kwargs)

    def get_move(self, mid: str, battle: AbstractBattle):
        for m in battle.available_moves or []:
            if m.id == mid:
                return m
        return None

    def opponent_remaining(self, battle:AbstractBattle) -> int:
        return sum(1 for p in battle.opponent_team.values() if not p.fainted)
    
    def teampreview(self, battle: AbstractBattle) -> str:
        return "/team 123456"

    def _stage_mult(self, stage: int) -> float:
        s = max(-6, min(6, int(stage or 0)))
        return (2 + s) / 2 if s >= 0 else 2 / (2 - s)

    def _eff_with_chart(self, atk_type: PokemonType, d1: PokemonType | None, d2: PokemonType | None) -> float:
        chart = GenData.from_format(self.battle_format).type_chart 
        mult = 1.0
        if d1:
            mult *= chart[atk_type.name][d1.name]
        if d2:
            mult *= chart[atk_type.name][d2.name]
        return mult

    
    def expected_damage_score(self, attacker: Pokemon, defender: Pokemon, move : Move) -> float:
        if not move or (move.base_power or 0) <= 0:
            return 0.0

        base = move.base_power or 0
        if isinstance(move.accuracy, (int, float)):
            acc = (move.accuracy or 100) / 100.0
        else:
            acc = 1.0

        eff = self._eff_with_chart(move.type, defender.type_1, defender.type_2)
        if eff == 0.0:
            return 0.0

        stab = 1.5 if move.type in (attacker.type_1, attacker.type_2) else 1.0

        if move.category == MoveCategory.PHYSICAL:
            atk_stage = (attacker.boosts or {}).get("atk", 0)
            def_stage = (defender.boosts or {}).get("def", 0)
            burned = getattr(attacker, "status", None) and to_id_str(attacker.status.name) == "brn"
            burn = 0.5 if burned else 1.0
        else:
            atk_stage = (attacker.boosts or {}).get("spa", 0)
            def_stage = (defender.boosts or {}).get("spd", 0)
            burn = 1.0

        boost_ratio = self._stage_mult(atk_stage) / self._stage_mult(def_stage)

        return (base * acc * eff * stab * boost_ratio * burn) / 300.0

    def best_move_against(self, attacker: Pokemon, defender: Pokemon):
        best_m, best_s = None, 0.0
        for mv in (attacker.moves.values()):
            s = self.expected_damage_score(attacker, defender, mv)
            if s > best_s:
                best_m, best_s = mv, s
        return best_m, best_s
        
    def _choose_pivot(self, battle: AbstractBattle, opp: Pokemon) -> Pokemon:
        best_sw, best_val = None, -999.0
        for sw in battle.available_switches:
            if to_id_str(sw.species) == "landorustherian":
                continue  
            best_move_val = 0.0
            for mv in (sw.moves or {}).values():
                best_move_val = max(best_move_val, self._score_move_live(sw, opp, mv))
            net = best_move_val - self._hazard_tax_fraction(battle, sw)
            sid = to_id_str(sw.species)
            if sid == "hooh" and battle.turn <= 6:
                net += 0.05
            if sid in ("arceus", "kingambit") and battle.turn <= 6:
                net -= 0.05
            if net > best_val:
                best_val, best_sw = net, sw
        return best_sw
    
    def choose_move(self, battle: AbstractBattle):

        me: Pokemon =  battle.active_pokemon
        opp: Pokemon = battle.opponent_active_pokemon

        if battle.turn == 1 and me.species == "kingambit":
            #s switch
            pass

        if battle.force_switch or not me:
            sw = self._choose_pivot(battle, opp)
            return self.create_order(sw)
        
        if me.species == "landorustherian":
            if SideCondition.STEALTH_ROCK not in battle.opponent_side_conditions and self.opponent_remaining(battle) >= 4:
                sr = self.get_move("stealthrock")
                if sr:
                    return self.create_order(sr)

        best_m, best_s = self.best_move_against(me, opp)

        if best_m and best_s >= DMG_THRESHOLD:
            return self.create_order(best_m)

        return self.choose_random_move(battle)

        