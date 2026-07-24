from dataclasses import dataclass
from typing import Dict, Tuple

from apworld.toontown import ITEM_NAME_TO_ID, ToontownItemName


TREE_BEANS = "beans"
TREE_SHIELD = "shield"
TREE_UBER = "uber"
TREE_GAGS = "gags"


@dataclass(frozen=True)
class TrapSkill:
    skill_id: int
    key: str
    name: str
    cost: int
    tree: str
    requires: Tuple[int, ...] = ()
    locks: Tuple[int, ...] = ()
    trap_item_ids: Tuple[int, ...] = ()
    tax_amount: int = 0

    @property
    def trap_item_id(self) -> int:
        return self.trap_item_ids[0] if self.trap_item_ids else 0


def _item(name: ToontownItemName) -> int:
    return ITEM_NAME_TO_ID[name.value]


BEAN_TAX_BASE = 1
BEAN_TAX_750 = 2
BEAN_TAX_1000 = 3
BEAN_TAX_1250 = 4
BEAN_EXPOSE = 5
BEAN_TAX_DAMAGE_1 = 6
BEAN_TAX_DAMAGE_2 = 7

SHIELD_BASE = 20
SHIELD_TIMER_2X = 21
SHIELD_DURABILITY_2X = 22
SHIELD_BACKFIRE = 23
SHIELD_BREAKER = 24
SHIELD_BREAKER_2X = 25
SHIELD_DRAIN_TIMER_2X = 26

UBER_CASHBOT = 40
UBER_DAMAGE_10 = 41
UBER_DAMAGE_15 = 42
UBER_DAMAGE_25 = 43
UBER_FOUR_GAG = 44
UBER_THREE_GAG = 45
UBER_TWO_GAG = 46

TRACK_DISABLE_BASE = 60
TRACK_DISABLE_TIMER_2X = 61
TRACK_DISABLE_TWO_TRACK = 62
GAG_SHUFFLE_SMALL = 63
GAG_SHUFFLE_MEDIUM = 64
GAG_SHUFFLE_LARGE = 65


TRAP_SKILLS: Dict[int, TrapSkill] = {
    BEAN_TAX_BASE: TrapSkill(
        BEAN_TAX_BASE, "bean_tax_500", "500 JB Tax", 1, TREE_BEANS,
        trap_item_ids=(_item(ToontownItemName.BEAN_TAX_TRAP_500),), tax_amount=500,
    ),
    BEAN_TAX_750: TrapSkill(
        BEAN_TAX_750, "bean_tax_750", "750 Bean Tax", 2, TREE_BEANS,
        requires=(BEAN_TAX_BASE,), locks=(BEAN_EXPOSE, BEAN_TAX_DAMAGE_1, BEAN_TAX_DAMAGE_2),
        trap_item_ids=(_item(ToontownItemName.BEAN_TAX_TRAP_750),), tax_amount=750,
    ),
    BEAN_TAX_1000: TrapSkill(
        BEAN_TAX_1000, "bean_tax_1000", "1000 Bean Tax", 3, TREE_BEANS,
        requires=(BEAN_TAX_750,), trap_item_ids=(_item(ToontownItemName.BEAN_TAX_TRAP_1000),),
        tax_amount=1000,
    ),
    BEAN_TAX_1250: TrapSkill(
        BEAN_TAX_1250, "bean_tax_1250", "1250 Bean Tax", 4, TREE_BEANS,
        requires=(BEAN_TAX_1000,), trap_item_ids=(_item(ToontownItemName.BEAN_TAX_TRAP_1250),),
        tax_amount=1250,
    ),
    BEAN_EXPOSE: TrapSkill(
        BEAN_EXPOSE, "bean_expose", "Jellybean Expose", 2, TREE_BEANS,
        requires=(BEAN_TAX_BASE,), locks=(BEAN_TAX_750, BEAN_TAX_1000, BEAN_TAX_1250),
        trap_item_ids=(_item(ToontownItemName.EXPOSE_BEANS_TRAP),),
    ),
    BEAN_TAX_DAMAGE_1: TrapSkill(
        BEAN_TAX_DAMAGE_1, "bean_tax_damage_1", "Tax Damage I", 3, TREE_BEANS,
        requires=(BEAN_EXPOSE,),
    ),
    BEAN_TAX_DAMAGE_2: TrapSkill(
        BEAN_TAX_DAMAGE_2, "bean_tax_damage_2", "Tax Damage II", 4, TREE_BEANS,
        requires=(BEAN_TAX_DAMAGE_1,),
    ),

    SHIELD_BASE: TrapSkill(
        SHIELD_BASE, "shield_reflect", "Shield", 1, TREE_SHIELD,
        trap_item_ids=(_item(ToontownItemName.TRAP_REFLECT),),
    ),
    SHIELD_TIMER_2X: TrapSkill(
        SHIELD_TIMER_2X, "shield_timer_2x", "2x Timer", 2, TREE_SHIELD,
        requires=(SHIELD_BASE,), locks=(SHIELD_BREAKER, SHIELD_BREAKER_2X, SHIELD_DRAIN_TIMER_2X),
    ),
    SHIELD_DURABILITY_2X: TrapSkill(
        SHIELD_DURABILITY_2X, "shield_durability_2x", "2x Durability", 3, TREE_SHIELD,
        requires=(SHIELD_TIMER_2X,),
    ),
    SHIELD_BACKFIRE: TrapSkill(
        SHIELD_BACKFIRE, "shield_backfire", "Backfire", 4, TREE_SHIELD,
        requires=(SHIELD_DURABILITY_2X,),
    ),
    SHIELD_BREAKER: TrapSkill(
        SHIELD_BREAKER, "shield_breaker", "Shield Breaker", 2, TREE_SHIELD,
        requires=(SHIELD_BASE,), locks=(SHIELD_TIMER_2X, SHIELD_DURABILITY_2X, SHIELD_BACKFIRE),
        trap_item_ids=(_item(ToontownItemName.DRIP_TRAP), _item(ToontownItemName.SHIELD_BREAKER_TRAP)),
    ),
    SHIELD_BREAKER_2X: TrapSkill(
        SHIELD_BREAKER_2X, "shield_breaker_2x", "2x Breaker", 3, TREE_SHIELD,
        requires=(SHIELD_BREAKER,),
    ),
    SHIELD_DRAIN_TIMER_2X: TrapSkill(
        SHIELD_DRAIN_TIMER_2X, "shield_drain_timer_2x", "Drain Timers", 4, TREE_SHIELD,
        requires=(SHIELD_BREAKER_2X,),
    ),

    UBER_CASHBOT: TrapSkill(
        UBER_CASHBOT, "cashbot_uber", "Cashbot Uber", 1, TREE_UBER,
        trap_item_ids=(_item(ToontownItemName.CASHBOT_UBER_TRAP),),
    ),
    UBER_DAMAGE_10: TrapSkill(
        UBER_DAMAGE_10, "damage_10", "10% Damage", 2, TREE_UBER,
        requires=(UBER_CASHBOT,), locks=(UBER_FOUR_GAG, UBER_THREE_GAG, UBER_TWO_GAG),
        trap_item_ids=(_item(ToontownItemName.DAMAGE_10),),
    ),
    UBER_DAMAGE_15: TrapSkill(
        UBER_DAMAGE_15, "damage_15", "15% Damage", 3, TREE_UBER,
        requires=(UBER_DAMAGE_10,), trap_item_ids=(_item(ToontownItemName.DAMAGE_15),),
    ),
    UBER_DAMAGE_25: TrapSkill(
        UBER_DAMAGE_25, "damage_25", "25% Damage", 4, TREE_UBER,
        requires=(UBER_DAMAGE_15,), trap_item_ids=(_item(ToontownItemName.DAMAGE_25),),
    ),
    UBER_FOUR_GAG: TrapSkill(
        UBER_FOUR_GAG, "four_gag_uber", "4 Gag Uber", 2, TREE_UBER,
        requires=(UBER_CASHBOT,), locks=(UBER_DAMAGE_10, UBER_DAMAGE_15, UBER_DAMAGE_25),
        trap_item_ids=(_item(ToontownItemName.FOUR_GAG_UBER_TRAP),),
    ),
    UBER_THREE_GAG: TrapSkill(
        UBER_THREE_GAG, "three_gag_uber", "3 Gag Uber", 3, TREE_UBER,
        requires=(UBER_FOUR_GAG,), trap_item_ids=(_item(ToontownItemName.THREE_GAG_UBER_TRAP),),
    ),
    UBER_TWO_GAG: TrapSkill(
        UBER_TWO_GAG, "two_gag_uber", "2 Gag Uber", 4, TREE_UBER,
        requires=(UBER_THREE_GAG,), trap_item_ids=(_item(ToontownItemName.UBER_TRAP),),
    ),

    TRACK_DISABLE_BASE: TrapSkill(
        TRACK_DISABLE_BASE, "track_disable_1", "Track Disable", 1, TREE_GAGS,
        trap_item_ids=(_item(ToontownItemName.GAG_DISABLE_TRAP),),
    ),
    TRACK_DISABLE_TIMER_2X: TrapSkill(
        TRACK_DISABLE_TIMER_2X, "track_disable_timer_2x", "2x Timer", 2, TREE_GAGS,
        requires=(TRACK_DISABLE_BASE,), locks=(GAG_SHUFFLE_SMALL, GAG_SHUFFLE_MEDIUM, GAG_SHUFFLE_LARGE),
    ),
    TRACK_DISABLE_TWO_TRACK: TrapSkill(
        TRACK_DISABLE_TWO_TRACK, "track_disable_two", "2 Track Disable", 3, TREE_GAGS,
        requires=(TRACK_DISABLE_TIMER_2X,), trap_item_ids=(_item(ToontownItemName.TWO_TRACK_DISABLE_TRAP),),
    ),
    GAG_SHUFFLE_SMALL: TrapSkill(
        GAG_SHUFFLE_SMALL, "gag_shuffle_small", "Small Shuffle", 2, TREE_GAGS,
        requires=(TRACK_DISABLE_BASE,), locks=(TRACK_DISABLE_TIMER_2X, TRACK_DISABLE_TWO_TRACK),
        trap_item_ids=(_item(ToontownItemName.SMALL_GAG_SHUFFLE_TRAP),),
    ),
    GAG_SHUFFLE_MEDIUM: TrapSkill(
        GAG_SHUFFLE_MEDIUM, "gag_shuffle_medium", "Medium Shuffle", 3, TREE_GAGS,
        requires=(GAG_SHUFFLE_SMALL,), trap_item_ids=(_item(ToontownItemName.MEDIUM_GAG_SHUFFLE_TRAP),),
    ),
    GAG_SHUFFLE_LARGE: TrapSkill(
        GAG_SHUFFLE_LARGE, "gag_shuffle_large", "Large Shuffle", 4, TREE_GAGS,
        requires=(GAG_SHUFFLE_MEDIUM,), trap_item_ids=(_item(ToontownItemName.GAG_SHUFFLE_TRAP),),
    ),
}

TREE_TITLES = {
    TREE_BEANS: "Beans",
    TREE_SHIELD: "Shield/Expose",
    TREE_UBER: "Uber",
    TREE_GAGS: "Gags",
}

TREE_ORDER = (TREE_BEANS, TREE_SHIELD, TREE_UBER, TREE_GAGS)

TREE_SKILL_ORDER = {
    TREE_BEANS: (
        BEAN_TAX_1250, BEAN_TAX_1000, BEAN_TAX_750,
        BEAN_TAX_DAMAGE_2, BEAN_TAX_DAMAGE_1, BEAN_EXPOSE,
        BEAN_TAX_BASE,
    ),
    TREE_SHIELD: (
        SHIELD_BACKFIRE, SHIELD_DURABILITY_2X, SHIELD_TIMER_2X,
        SHIELD_DRAIN_TIMER_2X, SHIELD_BREAKER_2X, SHIELD_BREAKER,
        SHIELD_BASE,
    ),
    TREE_UBER: (
        UBER_DAMAGE_25, UBER_DAMAGE_15, UBER_DAMAGE_10,
        UBER_TWO_GAG, UBER_THREE_GAG, UBER_FOUR_GAG,
        UBER_CASHBOT,
    ),
    TREE_GAGS: (
        TRACK_DISABLE_TWO_TRACK, TRACK_DISABLE_TIMER_2X,
        GAG_SHUFFLE_LARGE, GAG_SHUFFLE_MEDIUM, GAG_SHUFFLE_SMALL,
        TRACK_DISABLE_BASE,
    ),
}

TREE_POSITIONS = {
    TREE_BEANS: {
        BEAN_TAX_BASE: (0.0, -0.29),
        BEAN_TAX_750: (-0.22, -0.13),
        BEAN_TAX_1000: (-0.33, 0.04),
        BEAN_TAX_1250: (-0.43, 0.20),
        BEAN_EXPOSE: (0.22, -0.13),
        BEAN_TAX_DAMAGE_1: (0.33, 0.04),
        BEAN_TAX_DAMAGE_2: (0.43, 0.20),
    },
    TREE_SHIELD: {
        SHIELD_BASE: (0.0, -0.29),
        SHIELD_TIMER_2X: (-0.22, -0.13),
        SHIELD_DURABILITY_2X: (-0.33, 0.04),
        SHIELD_BACKFIRE: (-0.43, 0.20),
        SHIELD_BREAKER: (0.22, -0.13),
        SHIELD_BREAKER_2X: (0.33, 0.04),
        SHIELD_DRAIN_TIMER_2X: (0.43, 0.20),
    },
    TREE_UBER: {
        UBER_CASHBOT: (0.0, -0.29),
        UBER_DAMAGE_10: (-0.22, -0.13),
        UBER_DAMAGE_15: (-0.33, 0.04),
        UBER_DAMAGE_25: (-0.43, 0.20),
        UBER_FOUR_GAG: (0.22, -0.13),
        UBER_THREE_GAG: (0.33, 0.04),
        UBER_TWO_GAG: (0.43, 0.20),
    },
    TREE_GAGS: {
        TRACK_DISABLE_BASE: (0.0, -0.29),
        TRACK_DISABLE_TIMER_2X: (-0.22, -0.13),
        TRACK_DISABLE_TWO_TRACK: (-0.33, 0.04),
        GAG_SHUFFLE_SMALL: (0.22, -0.13),
        GAG_SHUFFLE_MEDIUM: (0.33, 0.04),
        GAG_SHUFFLE_LARGE: (0.43, 0.20),
    },
}


def sorted_skill_ids():
    return sorted(TRAP_SKILLS)


def spent_skill_points(skill_ids):
    return sum(TRAP_SKILLS[int(skill_id)].cost for skill_id in skill_ids if int(skill_id) in TRAP_SKILLS)


def has_skill(skill_ids, skill_id):
    return int(skill_id) in {int(existing) for existing in skill_ids}
