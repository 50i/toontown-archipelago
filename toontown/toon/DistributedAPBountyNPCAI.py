from .DistributedNPCToonBaseAI import DistributedNPCToonBaseAI
from toontown.archipelago.definitions.bounties import BOUNTY_OFFER_COUNT, MAX_ACTIVE_BOUNTIES, make_bounty, normalize_bounty


AP_BOUNTY_MOVIE_CLEAR = 0
AP_BOUNTY_MOVIE_START = 1
AP_BOUNTY_MOVIE_ACCEPT = 2
AP_BOUNTY_MOVIE_CLOSE = 3
AP_BOUNTY_MOVIE_FULL = 4


class DistributedAPBountyNPCAI(DistributedNPCToonBaseAI):
    def __init__(self, air, npcId=119920):
        DistributedNPCToonBaseAI.__init__(self, air, npcId)
        self.busy = 0
        self.pendingOffers = {}
        self.bountyOffers = {}

    def avatarEnter(self):
        avId = self.air.getAvatarIdFromSender()
        av = self.air.doId2do.get(avId)
        if av is None:
            return
        if self.busy and self.busy != avId:
            return

        self.busy = avId
        active = av.getAPBounties()
        if len(active) >= MAX_ACTIVE_BOUNTIES:
            self.pendingOffers[avId] = []
            self.sendUpdate('setBountyState', [AP_BOUNTY_MOVIE_FULL, avId, []])
            self._clear(avId)
            return

        offers = self.bountyOffers.get(avId)
        if not offers:
            offers = [make_bounty(av, slot) for slot in range(BOUNTY_OFFER_COUNT)]
            self.bountyOffers[avId] = offers
        self.pendingOffers[avId] = offers
        self.sendUpdate('setBountyState', [AP_BOUNTY_MOVIE_START, avId, offers])

    def acceptBounty(self, bountyId):
        avId = self.air.getAvatarIdFromSender()
        if self.busy != avId:
            return
        av = self.air.doId2do.get(avId)
        if av is None:
            self._clear(avId)
            return
        if len(av.getAPBounties()) >= MAX_ACTIVE_BOUNTIES:
            self.sendUpdate('setBountyState', [AP_BOUNTY_MOVIE_FULL, avId, []])
            self._clear(avId)
            return

        bountyId = int(bountyId)
        offers = [normalize_bounty(offer) for offer in self.pendingOffers.get(avId, [])]
        selected = None
        for offer in offers:
            if offer[0] == bountyId:
                selected = offer
                break
        if selected is None:
            return

        av.addAPBounty(selected)
        if avId in self.bountyOffers:
            self.bountyOffers[avId] = [offer for offer in self.bountyOffers[avId] if normalize_bounty(offer)[0] != bountyId]
        self.sendUpdate('setBountyState', [AP_BOUNTY_MOVIE_ACCEPT, avId, [selected]])
        self._clear(avId)

    def closeBountyGui(self):
        avId = self.air.getAvatarIdFromSender()
        if self.busy != avId:
            return
        self.sendUpdate('setBountyState', [AP_BOUNTY_MOVIE_CLOSE, avId, []])
        self._clear(avId)

    def _clear(self, avId):
        self.pendingOffers.pop(avId, None)
        if self.busy == avId:
            self.busy = 0
