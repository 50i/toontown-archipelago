import random
import time

from .DistributedNPCToonBaseAI import DistributedNPCToonBaseAI
from apworld.toontown import ITEM_NAME_TO_ID, ToontownItemName, get_item_def_from_id
from toontown.archipelago.definitions.rewards import EarnedAPReward, get_ap_reward_from_id


AP_VENDOR_MOVIE_CLEAR = 0
AP_VENDOR_MOVIE_START = 1
AP_VENDOR_MOVIE_BUY = 2
AP_VENDOR_MOVIE_CLOSE = 3
AP_VENDOR_MOVIE_NO_MONEY = 4


class DistributedAPVendorNPCAI(DistributedNPCToonBaseAI):
    ITEM_CATEGORIES = (
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

    def __init__(self, air, npcId=0, vendorType=0):
        DistributedNPCToonBaseAI.__init__(self, air, npcId)
        self.vendorType = int(vendorType)
        self.busy = 0
        self.price = 0

    def setVendorType(self, vendorType):
        self.vendorType = int(vendorType)

    def getVendorType(self):
        return self.vendorType

    def avatarEnter(self):
        avId = self.air.getAvatarIdFromSender()
        av = self.air.doId2do.get(avId)
        if av is None:
            return
        if self.busy and self.busy != avId:
            return
        self.busy = avId
        self.price = random.randint(1000, 2000)
        self.sendUpdate('setVendorState', [AP_VENDOR_MOVIE_START, avId, self.price])

    def buyRandomItem(self):
        avId = self.air.getAvatarIdFromSender()
        if self.busy != avId:
            return
        av = self.air.doId2do.get(avId)
        if av is None:
            self.busy = 0
            self.price = 0
            return
        price = self.price or random.randint(1000, 2000)
        if av.getMoney() < price:
            self.sendUpdate('setVendorState', [AP_VENDOR_MOVIE_NO_MONEY, avId, price])
            return

        itemId = self._chooseItemId()
        itemDef = get_item_def_from_id(itemId)
        reward = get_ap_reward_from_id(itemId)
        rewardIndex = self._nextVendorRewardIndex(av, itemId)
        av.takeMoney(price)
        av.queueAPReward(EarnedAPReward(av, reward, rewardIndex, itemId, self.getName(), True))
        av.addReceivedItem(rewardIndex, itemId)
        if itemDef is not None:
            print(f"[AP VENDOR] {av.getName()} bought {itemDef.name.value} from {self.getName()} for {price} beans; inserted location: {self.getName()} ({rewardIndex})")
            av.d_sendArchipelagoMessage(f"{self.getName()} sold you {itemDef.name.value} for {price} jellybeans.")
        self.sendUpdate('setVendorState', [AP_VENDOR_MOVIE_BUY, avId, price])
        self.busy = 0
        self.price = 0

    def closeShop(self):
        avId = self.air.getAvatarIdFromSender()
        if self.busy != avId:
            return
        self.sendUpdate('setVendorState', [AP_VENDOR_MOVIE_CLOSE, avId, self.price])
        self.busy = 0
        self.price = 0

    def _chooseItemId(self):
        weights = [weight for weight, _items in self.ITEM_CATEGORIES]
        category = random.choices(self.ITEM_CATEGORIES, weights=weights)[0][1]
        return ITEM_NAME_TO_ID[random.choice(category).value]

    def _nextVendorRewardIndex(self, av, itemId):
        index = 925000000000 + (self.vendorType * 100000000) + (int(time.time() * 1000) % 100000000)
        usedIndexes = {rewardIndex for rewardIndex, _itemId in av.getReceivedItems()}
        while index in usedIndexes:
            index += 1
        return index
