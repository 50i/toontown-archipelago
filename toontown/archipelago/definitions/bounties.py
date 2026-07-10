import random
import time

from apworld.toontown import ITEM_NAME_TO_ID, ToontownItemName, get_item_def_from_id


MAX_ACTIVE_BOUNTIES = 1
BOUNTY_OFFER_COUNT = 3

OBJECTIVE_BOSSES = 'bosses'
OBJECTIVE_COGS = 'cogs'
OBJECTIVE_DEPT_PREFIX = 'dept:'
OBJECTIVE_ITEM_PREFIX = 'item:'

DEPT_OBJECTIVE_NAMES = {
    'c': 'Bossbots',
    'l': 'Lawbots',
    'm': 'Cashbots',
    's': 'Sellbots',
}

BOUNTY_OBJECTIVE_TEMPLATES = (
    (OBJECTIVE_BOSSES, 1, 4),
    (OBJECTIVE_COGS, 120, 300),
    (OBJECTIVE_DEPT_PREFIX + 'c', 60, 160),
    (OBJECTIVE_DEPT_PREFIX + 'l', 60, 160),
    (OBJECTIVE_DEPT_PREFIX + 'm', 60, 160),
    (OBJECTIVE_DEPT_PREFIX + 's', 60, 160),
    (OBJECTIVE_ITEM_PREFIX + ToontownItemName.FISHING_ROD_UPGRADE.value, 2, 4),
    (OBJECTIVE_ITEM_PREFIX + ToontownItemName.MONEY_CAP_1000.value, 4, 9),
    (OBJECTIVE_ITEM_PREFIX + ToontownItemName.TASK_CAPACITY.value, 2, 4),
    (OBJECTIVE_ITEM_PREFIX + ToontownItemName.SELLBOT_DISGUISE.value, 1, 1),
    (OBJECTIVE_ITEM_PREFIX + ToontownItemName.CASHBOT_DISGUISE.value, 1, 1),
    (OBJECTIVE_ITEM_PREFIX + ToontownItemName.LAWBOT_DISGUISE.value, 1, 1),
    (OBJECTIVE_ITEM_PREFIX + ToontownItemName.BOSSBOT_DISGUISE.value, 1, 1),
)

BOUNTY_REWARD_CATEGORIES = (
    (30, (
        ToontownItemName.TTC_ACCESS,
        ToontownItemName.DD_ACCESS,
        ToontownItemName.DG_ACCESS,
        ToontownItemName.MML_ACCESS,
        ToontownItemName.TB_ACCESS,
        ToontownItemName.DDL_ACCESS,
        ToontownItemName.SBHQ_ACCESS,
        ToontownItemName.CBHQ_ACCESS,
        ToontownItemName.LBHQ_ACCESS,
        ToontownItemName.BBHQ_ACCESS,
        ToontownItemName.AA_ACCESS,
        ToontownItemName.GS_ACCESS,
    )),
    (26, (
        ToontownItemName.FRONT_FACTORY_ACCESS,
        ToontownItemName.SIDE_FACTORY_ACCESS,
        ToontownItemName.COIN_MINT_ACCESS,
        ToontownItemName.DOLLAR_MINT_ACCESS,
        ToontownItemName.BULLION_MINT_ACCESS,
        ToontownItemName.A_OFFICE_ACCESS,
        ToontownItemName.B_OFFICE_ACCESS,
        ToontownItemName.C_OFFICE_ACCESS,
        ToontownItemName.D_OFFICE_ACCESS,
        ToontownItemName.FRONT_ONE_ACCESS,
        ToontownItemName.MIDDLE_TWO_ACCESS,
        ToontownItemName.BACK_THREE_ACCESS,
    )),
    (24, (
        ToontownItemName.SELLBOT_DISGUISE,
        ToontownItemName.CASHBOT_DISGUISE,
        ToontownItemName.LAWBOT_DISGUISE,
        ToontownItemName.BOSSBOT_DISGUISE,
    )),
    (20, (
        ToontownItemName.TTC_JOKE_BOOK,
        ToontownItemName.DD_JOKE_BOOK,
        ToontownItemName.DG_JOKE_BOOK,
        ToontownItemName.MML_JOKE_BOOK,
        ToontownItemName.TB_JOKE_BOOK,
        ToontownItemName.DDL_JOKE_BOOK,
    )),
)

BOUNTY_REPLACEMENT_CATEGORIES = (
    (42, (
        ToontownItemName.XP_10,
        ToontownItemName.XP_15,
        ToontownItemName.XP_20,
        ToontownItemName.GAG_MULTIPLIER_1,
        ToontownItemName.GAG_MULTIPLIER_2,
    )),
    (38, (
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
    )),
    (20, (
        ToontownItemName.MONEY_400,
        ToontownItemName.MONEY_700,
        ToontownItemName.MONEY_1000,
        ToontownItemName.SOS_REWARD_4,
        ToontownItemName.SOS_REWARD_5,
    )),
)


def choose_bounty_reward_item_id(av=None):
    weights = [weight for weight, _items in BOUNTY_REWARD_CATEGORIES]
    for _attempt in range(20):
        category = random.choices(BOUNTY_REWARD_CATEGORIES, weights=weights)[0][1]
        item_id = ITEM_NAME_TO_ID[random.choice(category).value]
        if av is None or _effective_item_count(av, item_id) <= 0:
            return item_id
    category = random.choices(BOUNTY_REWARD_CATEGORIES, weights=weights)[0][1]
    return ITEM_NAME_TO_ID[random.choice(category).value]


def choose_bounty_replacement_item_id():
    weights = [weight for weight, _items in BOUNTY_REPLACEMENT_CATEGORIES]
    category = random.choices(BOUNTY_REPLACEMENT_CATEGORIES, weights=weights)[0][1]
    return ITEM_NAME_TO_ID[random.choice(category).value]


def make_bounty(av, offer_slot=0):
    target, required = _choose_objective(av)
    bounty_id = _next_bounty_id(av, offer_slot)
    return [
        bounty_id,
        target,
        required,
        get_objective_progress(av, target),
        choose_bounty_reward_item_id(av),
    ]


def describe_bounty(bounty):
    bounty_id, target, required, progress, item_id = normalize_bounty(bounty)
    reward = get_reward_name(item_id)
    objective = get_objective_text(target, required)
    return bounty_id, objective, '%s/%s' % (min(progress, required), required), reward


def get_objective_text(target, required):
    if target == OBJECTIVE_BOSSES:
        return 'Defeat %s Cog Bosses' % required
    if target == OBJECTIVE_COGS:
        return 'Defeat %s Cogs' % required
    if target.startswith(OBJECTIVE_DEPT_PREFIX):
        dept = target[len(OBJECTIVE_DEPT_PREFIX):]
        return 'Defeat %s %s' % (required, DEPT_OBJECTIVE_NAMES.get(dept, 'Cogs'))
    if target.startswith(OBJECTIVE_ITEM_PREFIX):
        item_name = target[len(OBJECTIVE_ITEM_PREFIX):]
        if item_name == ToontownItemName.FISHING_ROD_UPGRADE.value:
            return 'Obtain Gold Rod'
        if item_name == ToontownItemName.MONEY_CAP_1000.value:
            return 'Obtain All Jellybean Jars'
        if item_name == ToontownItemName.TASK_CAPACITY.value:
            return 'Max Task Capacity'
        return 'Obtain %s' % item_name
    return 'Complete Bounty'


def get_reward_name(item_id):
    item_def = get_item_def_from_id(item_id)
    if item_def is None:
        return 'Random Item'
    return item_def.name.value


def get_objective_progress(av, target):
    if target.startswith(OBJECTIVE_ITEM_PREFIX):
        item_name = target[len(OBJECTIVE_ITEM_PREFIX):]
        item_id = ITEM_NAME_TO_ID.get(item_name)
        if item_id is None:
            return 0
        return _effective_item_count(av, item_id)
    return 0


def is_boss_defeat_record(suit):
    return bool(suit.get('isVP') or suit.get('isCFO'))


def normalize_bounty(bounty):
    normalized = list(bounty)
    if len(normalized) < 5:
        normalized.extend([0] * (5 - len(normalized)))
    normalized[0] = int(normalized[0])
    normalized[1] = str(normalized[1] or OBJECTIVE_COGS)
    normalized[2] = max(1, int(normalized[2]))
    normalized[3] = max(0, int(normalized[3]))
    normalized[4] = int(normalized[4])
    return normalized[:5]


def _choose_objective(av):
    available = []
    for target, minimum, maximum in BOUNTY_OBJECTIVE_TEMPLATES:
        required = random.randint(minimum, maximum)
        if get_objective_progress(av, target) < required:
            available.append((target, required))
    if not available:
        available = [(OBJECTIVE_BOSSES, random.randint(1, 4)), (OBJECTIVE_COGS, random.randint(120, 300))]
    return random.choice(available)


def _effective_item_count(av, item_id):
    if hasattr(av, 'getEffectiveReceivedItemCount'):
        return av.getEffectiveReceivedItemCount(item_id)
    return sum(1 for _index, received_item_id in av.getReceivedItems() if received_item_id == item_id)


def _next_bounty_id(av, offer_slot):
    seed = int(time.time() * 1000) % 100000000
    bounty_id = 930000000000 + (int(av.doId) * 1000000) + seed + int(offer_slot)
    used = {normalize_bounty(bounty)[0] for bounty in getattr(av, 'apBounties', [])}
    while bounty_id in used:
        bounty_id += 1
    return bounty_id
