from poke_env.battle import AbstractBattle
from poke_env.battle.move_category import MoveCategory
from poke_env.battle.pokemon import Pokemon
from poke_env.battle.side_condition import SideCondition
from poke_env.player import Player
from poke_env.battle.status import Status
from poke_env.battle.pokemon_type import PokemonType
from poke_env.data import to_id_str
import os, time
from typing import Dict, Tuple
from collections import defaultdict

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
        
    def choose_move(self, battle: AbstractBattle):
        me, opp = battle.active_pokemon, battle.opponent_active_pokemon
        pass