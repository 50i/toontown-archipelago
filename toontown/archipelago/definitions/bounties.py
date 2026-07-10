import random
import time

from apworld.toontown import ITEM_NAME_TO_ID, ToontownItemName, get_item_def_from_id
from toontown.suit import SuitDNA


MAX_ACTIVE_BOUNTIES = 4
BOUNTY_OFFER_COUNT = 3

BOUNTY_TARGETS = (
    ('any', 'Cogs', 8, 14),
    ('c', 'Bossbots', 5, 10),
    ('l', 'Lawbots', 5, 10),
    ('m', 'Cashbots', 5, 10),
    ('s', 'Sellbots', 5, 10),
)

BOUNTY_ITEM_CATEGORIES = (
    (48, (
        ToontownItemName.DRIP_TRAP,
        ToontownItemName.UBER_TRAP,
        ToontownItemName.BEAN_TAX_TRAP_750,
        ToontownItemName.BEAN_TAX_TRAP_1000,
        ToontownItemName.BEAN_TAX_TRAP_1250,
        ToontownItemName.GAG_SHUFFLE_TRAP,
        ToontownItemName.EXPOSE_TRAP,
        ToontownItemName.EXPOSE_BEANS_TRAP,
        ToontownItemName.GAG_DISABLE_TRAP,
        ToontownItemName.TRAP_REFLECT,
        ToontownItemName.DAMAGE_15,
        ToontownItemName.DAMAGE_25,
    )),
    (34, (
        ToontownItemName.GAG_MULTIPLIER_1,
        ToontownItemName.GAG_MULTIPLIER_2,
    )),
    (10, (
        ToontownItemName.TOONUP_FRAME,
        ToontownItemName.TRAP_FRAME,
        ToontownItemName.LURE_FRAME,
        ToontownItemName.SOUND_FRAME,
        ToontownItemName.THROW_FRAME,
        ToontownItemName.SQUIRT_FRAME,
        ToontownItemName.DROP_FRAME,
    )),
    (5, (
        ToontownItemName.LAFF_BOOST_1,
        ToontownItemName.LAFF_BOOST_2,
        ToontownItemName.LAFF_BOOST_3,
        ToontownItemName.LAFF_BOOST_4,
        ToontownItemName.LAFF_BOOST_5,
    )),
    (3, (
        ToontownItemName.TOONUP_UPGRADE,
        ToontownItemName.TRAP_UPGRADE,
        ToontownItemName.LURE_UPGRADE,
        ToontownItemName.SOUND_UPGRADE,
        ToontownItemName.THROW_UPGRADE,
        ToontownItemName.SQUIRT_UPGRADE,
        ToontownItemName.DROP_UPGRADE,
    )),
)


def choose_bounty_reward_item_id():
    weights = [weight for weight, _items in BOUNTY_ITEM_CATEGORIES]
    category = random.choices(BOUNTY_ITEM_CATEGORIES, weights=weights)[0][1]
    return ITEM_NAME_TO_ID[random.choice(category).value]


def make_bounty(av, offer_slot=0):
    dept, _name, min_required, max_required = random.choice(BOUNTY_TARGETS)
    bounty_id = _next_bounty_id(av, offer_slot)
    return [
        bounty_id,
        dept,
        random.randint(min_required, max_required),
        0,
        choose_bounty_reward_item_id(),
    ]


def describe_bounty(bounty):
    bounty_id, dept, required, progress, item_id = normalize_bounty(bounty)
    target = get_target_name(dept)
    reward = get_reward_name(item_id)
    if dept == 'any':
        objective = 'Defeat %s Cogs' % required
    else:
        objective = 'Defeat %s %s' % (required, target)
    return bounty_id, objective, '%s/%s' % (min(progress, required), required), reward


def get_target_name(dept):
    if dept == 'any':
        return 'Cogs'
    return SuitDNA.getDeptFullnameP(dept)


def get_reward_name(item_id):
    item_def = get_item_def_from_id(item_id)
    if item_def is None:
        return 'Random Item'
    return item_def.name.value


def normalize_bounty(bounty):
    normalized = list(bounty)
    if len(normalized) < 5:
        normalized.extend([0] * (5 - len(normalized)))
    normalized[0] = int(normalized[0])
    normalized[1] = str(normalized[1] or 'any')
    normalized[2] = max(1, int(normalized[2]))
    normalized[3] = max(0, int(normalized[3]))
    normalized[4] = int(normalized[4])
    return normalized[:5]


def _next_bounty_id(av, offer_slot):
    seed = int(time.time() * 1000) % 100000000
    bounty_id = 930000000000 + (int(av.doId) * 1000000) + seed + int(offer_slot)
    used = {normalize_bounty(bounty)[0] for bounty in getattr(av, 'apBounties', [])}
    while bounty_id in used:
        bounty_id += 1
    return bounty_id
