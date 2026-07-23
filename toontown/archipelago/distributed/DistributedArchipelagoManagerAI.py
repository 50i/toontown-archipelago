import random
import time
from typing import Union, List

from direct.directnotify import DirectNotifyGlobal
from direct.distributed.DistributedObjectAI import DistributedObjectAI

from toontown.archipelago.apclient.ap_client_enums import APClientEnums
from toontown.archipelago.apclient.archipelago_session import ArchipelagoSession
from toontown.archipelago.definitions.rewards import EarnedAPReward, TrapReward, get_ap_reward_from_id
from toontown.archipelago.util.HintContainer import HintContainer, HintedItem
from toontown.archipelago.util.archipelago_information import ArchipelagoInformation
from toontown.toon.DistributedToonAI import DistributedToonAI
from toontown.coghq.CogDisguiseGlobals import PartsPerSuitBitmasks
from apworld.toontown import FISHING_LICENSES, ITEM_DEFINITIONS, ITEM_NAME_TO_ID, ToontownItemName, get_item_def_from_id
from apworld.toontown.fish import FishProgression


class DistributedArchipelagoManagerAI(DistributedObjectAI):
    notify = DirectNotifyGlobal.directNotify.newCategory("DistributedArchipelagoManagerAI")
    COMMUNITY_POLL_MIN_SECONDS = 10 * 60
    COMMUNITY_POLL_MAX_SECONDS = 15 * 60
    COMMUNITY_POLL_DURATION_SECONDS = 30

    def __init__(self, air):
        super().__init__(air)
        self.notify.debug("DistributedArchipelagoManager starting up....")

        # A cache of the last astron update sent, no need to use
        self.__previousSyncedInformation = []
        self.__pendingTrades = {}
        self.__raidTrapLocation = None
        self.__raidTrapClaimedBy = 0
        self.__communityPoll = None
        self.__communityPollSequence = 0

    def delete(self):
        taskMgr.remove(self.uniqueName('community-poll-start'))
        taskMgr.remove(self.uniqueName('community-poll-resolve'))
        super().delete()

    def announceGenerate(self):
        self.notify.debug(f"DistributedArchipelagoManager announceGenerate() with doId: {self.doId}")
        self.__scheduleCommunityPoll()

    def __scheduleCommunityPoll(self):
        taskMgr.remove(self.uniqueName('community-poll-start'))
        delay = random.randint(self.COMMUNITY_POLL_MIN_SECONDS, self.COMMUNITY_POLL_MAX_SECONDS)
        taskMgr.doMethodLater(delay, self.__startScheduledCommunityPoll, self.uniqueName('community-poll-start'))

    def __startScheduledCommunityPoll(self, task):
        self.startCommunityPoll()
        return task.done

    def __getPollParticipants(self):
        return [toon for toon in self.air.doFindAllInstances(DistributedToonAI) if toon.isPlayerControlled()]

    def startCommunityPoll(self):
        """Start one shared poll. Also invoked by the developer testing magic word."""
        if self.__communityPoll is not None:
            return False
        taskMgr.remove(self.uniqueName('community-poll-start'))

        participants = self.__getPollParticipants()
        if not participants:
            self.__scheduleCommunityPoll()
            return False

        outcome = random.choice(('grant_both', 'grant_one', 'trap_one', 'trap_both'))
        payload, description = self.__createCommunityPollPayload(outcome, participants)
        self.__communityPollSequence += 1
        pollId = self.__communityPollSequence
        self.__communityPoll = {
            'id': pollId,
            'outcome': outcome,
            'payload': payload,
            'description': description,
            'participants': {toon.doId for toon in participants},
            'responses': {},
        }
        for toon in participants:
            self.sendUpdateToAvatarId(toon.doId, 'showCommunityPoll', [pollId, description, self.COMMUNITY_POLL_DURATION_SECONDS])
        taskMgr.doMethodLater(self.COMMUNITY_POLL_DURATION_SECONDS, self.__resolveCommunityPoll, self.uniqueName('community-poll-resolve'))
        return True

    def voteCommunityPoll(self, pollId):
        self.__recordCommunityPollResponse(pollId, True)

    def declineCommunityPoll(self, pollId):
        self.__recordCommunityPollResponse(pollId, False)

    def __recordCommunityPollResponse(self, pollId, agrees):
        avId = self.air.getAvatarIdFromSender()
        poll = self.__communityPoll
        if poll is None or poll['id'] != pollId or avId not in poll['participants']:
            return
        poll['responses'][avId] = agrees
        if len(poll['responses']) == len(poll['participants']):
            # Do not make everyone wait out the clock once every player has voted.
            taskMgr.remove(self.uniqueName('community-poll-resolve'))
            taskMgr.doMethodLater(0, self.__resolveCommunityPoll, self.uniqueName('community-poll-resolve'))

    def __resolveCommunityPoll(self, task):
        poll = self.__communityPoll
        if poll is None:
            self.__scheduleCommunityPoll()
            return task.done

        participants = [self.air.doId2do.get(avId) for avId in poll['participants']]
        participants = [toon for toon in participants if toon is not None and toon.isPlayerControlled()]
        voteCount = sum(poll['responses'].get(toon.doId, False) for toon in participants)
        allOnlineAgreed = bool(participants) and all(poll['responses'].get(toon.doId) is True for toon in participants)
        successChance = 1.0 if allOnlineAgreed else 0.55 if voteCount == 1 else 0.75 if voteCount >= 2 else 0.0
        succeeded = bool(participants) and random.random() < successChance
        outcomeMessage = 'Nothing happened.'
        if succeeded:
            outcomeMessage = self.__applyCommunityPollOutcome(poll, participants)

        result = 'passed!' if succeeded else 'did not pass.'
        announcement = f"Community poll {result} {outcomeMessage}"
        for toon in participants:
            self.sendUpdateToAvatarId(toon.doId, 'clearCommunityPoll', [poll['id']])
        self.broadcastAPMessage(announcement)
        self.__communityPoll = None
        self.__scheduleCommunityPoll()
        return task.done

    def __usesFishingLicenses(self, toon):
        fishProgression = toon.slotData.get('fish_progression', FishProgression.Nonne)
        return fishProgression in (FishProgression.LicensesAndRods, FishProgression.Licenses)

    def __choosePollItem(self, targets):
        excludedItems = {
            ToontownItemName.VP,
            ToontownItemName.CFO,
            ToontownItemName.CJ,
            ToontownItemName.CEO,
        }
        licensesEnabled = all(self.__usesFishingLicenses(toon) for toon in targets)
        return random.choice([
            itemDef for itemDef in ITEM_DEFINITIONS
            if not isinstance(get_ap_reward_from_id(itemDef.unique_id), TrapReward)
            and itemDef.name not in excludedItems
            and (itemDef.name not in FISHING_LICENSES or licensesEnabled)
        ])

    def __choosePollTrap(self):
        return random.choice([itemDef for itemDef in ITEM_DEFINITIONS
                              if itemDef.name != ToontownItemName.RAID_TRAP
                              and isinstance(get_ap_reward_from_id(itemDef.unique_id), TrapReward)])

    def __createCommunityPollPayload(self, outcome, participants):
        if outcome == 'grant_both':
            itemDef = self.__choosePollItem(participants)
            return {'itemId': itemDef.unique_id, 'targetIds': [toon.doId for toon in participants]}, f"Grant {itemDef.name.value} to both Toons"
        if outcome == 'grant_one':
            target = random.choice(participants)
            itemDef = self.__choosePollItem([target])
            return {'itemId': itemDef.unique_id, 'targetIds': [target.doId]}, f"Grant {itemDef.name.value} to {target.getName()}"

        trapDef = self.__choosePollTrap()
        targets = participants if outcome == 'trap_both' else [random.choice(participants)]
        targetNames = 'both Toons' if outcome == 'trap_both' else targets[0].getName()
        return {'itemId': trapDef.unique_id, 'targetIds': [toon.doId for toon in targets]}, f"Trigger {trapDef.name.value} on {targetNames}"

    def __grantPollItem(self, toon, itemDef):
        rewardIndex = int(time.time() * 1000000) + toon.doId
        usedIndexes = {index for index, _itemId in toon.getReceivedItems()}
        while rewardIndex in usedIndexes:
            rewardIndex += 1
        toon.queueAPReward(EarnedAPReward(toon, get_ap_reward_from_id(itemDef.unique_id), rewardIndex, itemDef.unique_id, 'Community Poll', True))
        toon.addReceivedItem(rewardIndex, itemDef.unique_id)

    def __applyCommunityPollOutcome(self, poll, participants):
        itemDef = get_item_def_from_id(poll['payload']['itemId'])
        targets = [self.air.doId2do.get(avId) for avId in poll['payload']['targetIds']]
        targets = [toon for toon in targets if toon is not None and toon.isPlayerControlled()]
        if itemDef is None or not targets:
            return 'Nothing happened because the selected Toon was no longer online.'

        targetNames = ', '.join(toon.getName() for toon in targets)
        if poll['outcome'].startswith('grant'):
            for toon in targets:
                self.__grantPollItem(toon, itemDef)
                self.broadcastAPReward(toon.doId, itemDef.name.value, 'Community Poll')
            return f"Community Poll granted {itemDef.name.value} to {targetNames}."

        reward = get_ap_reward_from_id(itemDef.unique_id)
        for toon in targets:
            reward.apply(toon)
        return f"Community Poll triggered {itemDef.name.value} on {targetNames}."

    def broadcastAPMessage(self, message):
        """Send a cosmetic Archipelago announcement to every online Toon."""
        for toon in self.__getPollParticipants():
            self.sendUpdateToAvatarId(toon.doId, 'receiveAPBroadcast', [message])

    """
    Internal methods to make management easier
    """

    def __getToon(self, avId) -> Union[DistributedToonAI, None]:
        return self.air.doId2do.get(avId)

    def __getSession(self, avId) -> Union[ArchipelagoSession, None]:
        toon = self.__getToon(avId)
        if toon is None:
            return None

        # Is there a session defined?
        session = toon.archipelago_session
        if session is None:
            return None

        # If the toon is not connected to an AP server, then this should also be none.
        if session.client.state != APClientEnums.CONNECTED:
            return None

        return toon.archipelago_session

    # Returns a list of all Archipelago Sessions that are defined on any DistributedToonAI instances.
    def __getAllArchipelagoSessions(self) -> List[ArchipelagoSession]:
        sessions: List[ArchipelagoSession] = []

        # Loop through all online toons and extract the AP session if it exists.
        for toon in self.air.doFindAllInstances(DistributedToonAI):

            # Skip NPCs :3
            if not toon.isPlayerControlled():
                continue

            # If the toon has an AP session and it is connected add it
            if toon.archipelago_session is not None and toon.archipelago_session.client.state == APClientEnums.CONNECTED:
                sessions.append(toon.archipelago_session)

        return sessions

    """
    Public methods to be called for logic throughout the game's codebase
    """

    # Called when we need to make clients aware of information updates regarding slot/team IDs
    # todo In the future, we should refactor this to update specific toons dynamically but for now
    # todo we just want something to work
    def updateToonInfo(self, avId, slotId, teamId):
        infoToSend: List[ArchipelagoInformation] = []
        allApSessions = self.__getAllArchipelagoSessions()
        for session in allApSessions:
            infoToSend.append(ArchipelagoInformation(session.avatar.doId, session.getSlotId(), session.getTeamId()))

        self.d_sync(infoToSend)

    # Given an toon ID, return the ID of the team they are on.
    # Returns None if they are either not on a team, or not connected to Archipelago.
    def getToonTeam(self, avId) -> Union[int, None]:

        # See if we have a session
        session = self.__getSession(avId)
        if session is None:
            return None

        # See if we are on a valid team
        teamId = session.getTeamId()
        if teamId < 0:
            return None

        # We have a team!
        return teamId

    # Given two toon IDs, return whether or not they are on the same team.
    # This case is ONLY True when both toons are connected to archipelago and have a similar team slot.
    def onSameTeam(self, avId1, avId2) -> bool:
        team1 = self.getToonTeam(avId1)
        team2 = self.getToonTeam(avId2)

        # If either team1 or team2 is not on a team, they cannot be on the same team.
        if None in (team1, team2):
            return False

        # If the teams are equal, they are on the same team
        return team1 == team2

    # Given two toon IDs, return whether or not they are on enemy teams.
    # We define enemy teams as two opposing teams that does not include spectators.
    # This means that if either toon is not on a team, they will not be considered enemies.
    def onEnemyTeams(self, avId1, avId2) -> bool:
        toon1Team = self.getToonTeam(avId1)
        toon2Team = self.getToonTeam(avId2)

        # If either toon1 or toon2 is not on a team, they cannot be enemies.
        if None in (toon1Team, toon2Team):
            return False

        # If the teams are not equal, they are enemies.
        return toon1Team != toon2Team

    """
    Code related to cross-player AP reward visibility (cosmetic only)
    """

    # Called when a toon receives an AP item locally. Relays a cosmetic-only notice
    # to all *other* AP-connected toons so they can see it too, without touching
    # their own item/session state or granting them anything.
    def broadcastAPReward(self, sourceAvId, itemName, fromName):
        allApSessions = self.__getAllArchipelagoSessions()
        sourceToon = self.__getToon(sourceAvId)
        if sourceToon is None:
            return

        sourceDisplayName = sourceToon.getName()

        for session in allApSessions:
            targetAvId = session.avatar.doId

            # Don't echo the reward back to the toon that already saw it themselves
            if targetAvId == sourceAvId:
                continue

            self.d_broadcastAPReward(targetAvId, sourceDisplayName, itemName, fromName)

    def d_broadcastAPReward(self, targetAvId, sourceDisplayName, itemName, fromName):
        self.sendUpdateToAvatarId(targetAvId, 'receiveAPReward', [sourceDisplayName, itemName, fromName])

    """
    Code related to AP trade escrow
    """

    def __getItemName(self, itemId):
        itemDef = get_item_def_from_id(itemId)
        if itemDef is None:
            return None
        return itemDef.name.value

    def __sendTradeResult(self, avId, message):
        self.sendUpdateToAvatarId(avId, 'tradeResult', [message])

    def __hasReceivedItem(self, toon, rewardIndex, itemId):
        for receivedIndex, receivedItemId in toon.getReceivedItems():
            if receivedIndex == rewardIndex and receivedItemId == itemId:
                return True
        return (rewardIndex, itemId) in self.__getVirtualCogDisguiseItems(toon)

    def __getVirtualCogDisguiseItems(self, toon):
        deptToItem = {
            0: ToontownItemName.BOSSBOT_DISGUISE.value,
            1: ToontownItemName.LAWBOT_DISGUISE.value,
            2: ToontownItemName.CASHBOT_DISGUISE.value,
            3: ToontownItemName.SELLBOT_DISGUISE.value,
        }
        receivedItemIds = {itemId for _index, itemId in toon.getReceivedItems()}
        virtualItems = []
        for dept, itemName in deptToItem.items():
            itemId = ITEM_NAME_TO_ID[itemName]
            if itemId in receivedItemIds:
                continue
            try:
                if toon.getCogParts()[dept] != PartsPerSuitBitmasks[dept]:
                    continue
            except Exception:
                continue
            virtualItems.append((930000000000 + (toon.doId * 10) + dept, itemId))
        return virtualItems

    def __findReceivedItemIndex(self, toon, itemId, requestedIndex=None):
        for receivedIndex, receivedItemId in toon.getReceivedItems():
            if requestedIndex is not None and receivedIndex != requestedIndex:
                continue
            if receivedItemId == itemId:
                return receivedIndex
        for receivedIndex, receivedItemId in self.__getVirtualCogDisguiseItems(toon):
            if requestedIndex is not None and receivedIndex != requestedIndex:
                continue
            if receivedItemId == itemId:
                return receivedIndex
        return None

    def __getTradeInventoryStruct(self, toon):
        debtItemIds = {debt[1] for debt in toon.getAPTradeDebts()}
        items = []
        for receivedIndex, itemId in toon.getReceivedItems():
            if itemId in debtItemIds:
                continue
            if self.__getItemName(itemId) is None:
                continue
            items.append((receivedIndex, itemId))
        for receivedIndex, itemId in self.__getVirtualCogDisguiseItems(toon):
            if itemId in debtItemIds:
                continue
            if self.__getItemName(itemId) is None:
                continue
            items.append((receivedIndex, itemId))
        return [toon.doId, items]

    def requestTradeInventories(self):
        avId = self.air.getAvatarIdFromSender()
        inventories = []
        for session in self.__getAllArchipelagoSessions():
            inventories.append(self.__getTradeInventoryStruct(session.avatar))
        self.sendUpdateToAvatarId(avId, 'tradeInventories', [inventories])

    def __nextTradeIndex(self, toon, senderAvId, itemId):
        index = 900000000000 + (senderAvId * 1000000) + itemId
        usedIndexes = {receivedIndex for receivedIndex, _itemId in toon.getReceivedItems()}
        while index in usedIndexes:
            index += 1
        return index

    def __grantTradedItem(self, receiver, sender, itemId):
        rewardDefinition = get_ap_reward_from_id(itemId)
        tradeIndex = self.__nextTradeIndex(receiver, sender.doId, itemId)
        receiver.queueAPReward(EarnedAPReward(receiver, rewardDefinition, tradeIndex, itemId, sender.getName(), False))
        receiver.addReceivedItem(tradeIndex, itemId)

    def __removeTradedItemFromOwner(self, owner, rewardDefinition, rewardIndex, itemId):
        revoked = owner.revokeTradedAPReward(rewardDefinition, itemId)
        heldTrapRemoved = owner.removeHeldTrapByReward(rewardIndex, itemId)
        if isinstance(rewardDefinition, TrapReward):
            return 'held-trap' if heldTrapRemoved else None
        return 'revoked' if revoked else None

    def __restoreRemovedTradedItem(self, owner, rewardDefinition, rewardIndex, itemId, removalMode):
        if removalMode == 'held-trap':
            owner.holdTrap(EarnedAPReward(owner, rewardDefinition, rewardIndex, itemId, "Trade rollback", False))
        elif removalMode == 'revoked':
            rewardDefinition.apply(owner)

    def __chooseRaidTrapLocation(self):
        if self.__raidTrapLocation is not None:
            return self.__raidTrapLocation

        candidateIds = []
        seedName = "raid-trap"
        for session in self.__getAllArchipelagoSessions():
            slotData = getattr(session.avatar, 'slotData', {}) or {}
            seedName = slotData.get('seed_name', seedName)
            for location in slotData.get('local_locations', []):
                try:
                    candidateIds.append(int(location[0]))
                except (TypeError, ValueError, IndexError):
                    continue
            if candidateIds:
                break

        if not candidateIds:
            return None

        candidateIds = sorted(set(candidateIds))
        self.__raidTrapLocation = random.Random(f"raid-trap:{seedName}").choice(candidateIds)
        self.notify.warning(f"[AP RAID] RAID! trap location selected: {self.__raidTrapLocation}")
        return self.__raidTrapLocation

    def maybeGrantRaidTrap(self, toon, checkedLocations):
        if self.__raidTrapClaimedBy:
            return
        location = self.__chooseRaidTrapLocation()
        if location is None or location not in set(checkedLocations):
            return
        itemId = ITEM_NAME_TO_ID[ToontownItemName.RAID_TRAP.value]
        rewardIndex = 940000000000 + location
        rewardDefinition = get_ap_reward_from_id(itemId)
        toon.queueAPReward(EarnedAPReward(toon, rewardDefinition, rewardIndex, itemId, "RAID!", True))
        self.__raidTrapClaimedBy = toon.doId
        self.notify.warning(f"[AP RAID] {toon.getName()} claimed RAID! at location {location}")
        toon.d_sendArchipelagoMessage("RAID! trap found.")

    def requestTrade(self, targetAvId, offerIndex, offerItemId, requestedIndex, requestedItemId):
        requesterAvId = self.air.getAvatarIdFromSender()
        requester = self.__getToon(requesterAvId)
        target = self.__getToon(targetAvId)
        if requester is None or target is None or requesterAvId == targetAvId:
            self.__sendTradeResult(requesterAvId, "That trade target is not available.")
            return

        if self.__getSession(requesterAvId) is None:
            self.__sendTradeResult(requesterAvId, "Connect to Archipelago before trading.")
            return

        if not self.__hasReceivedItem(requester, offerIndex, offerItemId):
            self.__sendTradeResult(requesterAvId, "You do not have that AP item to offer.")
            return

        if requester.hasAPTradeDebtForItem(offerItemId):
            self.__sendTradeResult(requesterAvId, "Recover that traded item before trading it again.")
            return

        offerName = self.__getItemName(offerItemId)
        requestedName = self.__getItemName(requestedItemId)
        if offerName is None or requestedName is None:
            self.__sendTradeResult(requesterAvId, "That trade contains an unknown AP item.")
            return

        self.__pendingTrades[targetAvId] = (requesterAvId, offerIndex, offerItemId, requestedIndex, requestedItemId)
        self.sendUpdateToAvatarId(
            targetAvId,
            'tradeRequest',
            [requesterAvId, requester.getName(), offerIndex, offerItemId, requestedItemId, offerName, requestedName]
        )
        self.__sendTradeResult(requesterAvId, f"Trade offered to {target.getName()}.")

    def requestRaidTrade(self, targetAvId, offerIndex, offerItemId, requestedIndex, requestedItemId):
        requesterAvId = self.air.getAvatarIdFromSender()
        requester = self.__getToon(requesterAvId)
        if requester is None or not requester.consumeRaidTradeAuthorization():
            self.__sendTradeResult(requesterAvId, "RAID! is not active.")
            return
        self.__executeAcceptedTrade(requesterAvId, targetAvId, offerIndex, offerItemId, requestedIndex, requestedItemId, forced=True)

    def respondTrade(self, requesterAvId, accepted):
        targetAvId = self.air.getAvatarIdFromSender()
        pendingTrade = self.__pendingTrades.get(targetAvId)
        if pendingTrade is None or pendingTrade[0] != requesterAvId:
            self.__sendTradeResult(targetAvId, "That trade request is no longer active.")
            return

        self.__pendingTrades.pop(targetAvId, None)
        requester = self.__getToon(requesterAvId)
        target = self.__getToon(targetAvId)
        if requester is None or target is None:
            self.__sendTradeResult(targetAvId, "The other toon is no longer available.")
            return

        requesterAvId, offerIndex, offerItemId, requestedIndex, requestedItemId = pendingTrade
        if not accepted:
            target = self.__getToon(targetAvId)
            requester = self.__getToon(requesterAvId)
            if requester is not None:
                self.__sendTradeResult(requesterAvId, f"{target.getName()} declined your trade.")
            self.__sendTradeResult(targetAvId, "Trade declined.")
            return

        self.__executeAcceptedTrade(requesterAvId, targetAvId, offerIndex, offerItemId, requestedIndex, requestedItemId)

    def __executeAcceptedTrade(self, requesterAvId, targetAvId, offerIndex, offerItemId, requestedIndex, requestedItemId, forced=False):
        requester = self.__getToon(requesterAvId)
        target = self.__getToon(targetAvId)
        if requester is None or target is None or requesterAvId == targetAvId:
            self.__sendTradeResult(requesterAvId, "The other toon is no longer available.")
            if targetAvId:
                self.__sendTradeResult(targetAvId, "The other toon is no longer available.")
            return

        offerName = self.__getItemName(offerItemId)
        requestedName = self.__getItemName(requestedItemId)

        if offerName is None or requestedName is None:
            self.__sendTradeResult(requesterAvId, "Trade cancelled because an item is unknown.")
            self.__sendTradeResult(targetAvId, "Trade cancelled because an item is unknown.")
            return

        if not self.__hasReceivedItem(requester, offerIndex, offerItemId):
            self.__sendTradeResult(requesterAvId, "Trade cancelled because that AP item is gone.")
            self.__sendTradeResult(targetAvId, "Trade cancelled because the offered item is gone.")
            return

        requestedIndex = self.__findReceivedItemIndex(target, requestedItemId, requestedIndex)
        if requestedIndex is None:
            self.__sendTradeResult(requesterAvId, f"Trade cancelled because {target.getName()} does not have {requestedName}.")
            self.__sendTradeResult(targetAvId, f"Trade cancelled because you do not have {requestedName}.")
            return

        if target.hasAPTradeDebtForItem(requestedItemId):
            self.__sendTradeResult(requesterAvId, f"Trade cancelled because {target.getName()} is still recovering {requestedName}.")
            self.__sendTradeResult(targetAvId, f"Recover {requestedName} before trading it away.")
            return

        if requester.hasAPTradeDebtForItem(offerItemId):
            self.__sendTradeResult(requesterAvId, f"Recover {offerName} before trading it away.")
            self.__sendTradeResult(targetAvId, f"Trade cancelled because {requester.getName()} is still recovering {offerName}.")
            return

        requesterSession = self.__getSession(requesterAvId)
        targetSession = self.__getSession(targetAvId)
        if requesterSession is None or targetSession is None:
            self.__sendTradeResult(requesterAvId, "Trade cancelled because both players must be connected to Archipelago.")
            self.__sendTradeResult(targetAvId, "Trade cancelled because both players must be connected to Archipelago.")
            return

        offerReward = get_ap_reward_from_id(offerItemId)
        requestedReward = get_ap_reward_from_id(requestedItemId)

        requesterDebtId = requester.createAPTradeDebt(offerItemId, target.getName(), 0)
        targetDebtId = target.createAPTradeDebt(requestedItemId, requester.getName(), 0)
        requesterRemoval = self.__removeTradedItemFromOwner(requester, offerReward, offerIndex, offerItemId)
        targetRemoval = self.__removeTradedItemFromOwner(target, requestedReward, requestedIndex, requestedItemId)

        if requesterRemoval is None or targetRemoval is None:
            requester.removeAPTradeDebt(requesterDebtId)
            target.removeAPTradeDebt(targetDebtId)
            if requesterRemoval is not None:
                self.__restoreRemovedTradedItem(requester, offerReward, offerIndex, offerItemId, requesterRemoval)
            if targetRemoval is not None:
                self.__restoreRemovedTradedItem(target, requestedReward, requestedIndex, requestedItemId, targetRemoval)
            if requesterRemoval is None:
                self.__sendTradeResult(requesterAvId, f"Trade cancelled because {offerName} could not be removed from you.")
                self.__sendTradeResult(targetAvId, f"Trade cancelled because {offerName} could not be removed from {requester.getName()}.")
            else:
                self.__sendTradeResult(requesterAvId, f"Trade cancelled because {requestedName} could not be removed from {target.getName()}.")
                self.__sendTradeResult(targetAvId, f"Trade cancelled because {requestedName} could not be removed from you.")
            return

        requesterRecoveryLocation = requesterSession.client.pick_trade_recovery_location()
        targetRecoveryLocation = targetSession.client.pick_trade_recovery_location()

        if requesterRecoveryLocation is None or targetRecoveryLocation is None:
            requester.removeAPTradeDebt(requesterDebtId)
            target.removeAPTradeDebt(targetDebtId)
            self.__restoreRemovedTradedItem(requester, offerReward, offerIndex, offerItemId, requesterRemoval)
            self.__restoreRemovedTradedItem(target, requestedReward, requestedIndex, requestedItemId, targetRemoval)
            if requesterRecoveryLocation is None:
                self.__sendTradeResult(requesterAvId, "Trade cancelled: your offered item has no safe recovery location right now.")
                self.__sendTradeResult(targetAvId, "Trade cancelled: the item offered to you would softlock the other player.")
            else:
                self.__sendTradeResult(requesterAvId, "Trade cancelled: the requested item would softlock the other player.")
                self.__sendTradeResult(targetAvId, "Trade cancelled: your requested item has no safe recovery location right now.")
            return

        requester.setAPTradeDebtRecoveryLocation(requesterDebtId, requesterRecoveryLocation)
        target.setAPTradeDebtRecoveryLocation(targetDebtId, targetRecoveryLocation)

        requesterRecoveryName = requesterSession.client.describe_location(requesterRecoveryLocation)
        targetRecoveryName = targetSession.client.describe_location(targetRecoveryLocation)
        self.notify.warning(
            f"[AP TRADE] {requester.getName()} traded away {offerName}; "
            f"new recovery location in their seed: {requesterRecoveryName} ({requesterRecoveryLocation})"
        )
        self.notify.warning(
            f"[AP TRADE] {target.getName()} traded away {requestedName}; "
            f"new recovery location in their seed: {targetRecoveryName} ({targetRecoveryLocation})"
        )

        self.__grantTradedItem(target, requester, offerItemId)
        self.__grantTradedItem(requester, target, requestedItemId)

        self.__sendTradeResult(
            requesterAvId,
            f"{'RAID! ' if forced else ''}{target.getName()} {'was raided' if forced else 'accepted'}. You received {requestedName} for {offerName}."
        )
        self.__sendTradeResult(targetAvId, f"{'RAID! ' if forced else 'Accepted trade: '}received {offerName} for {requestedName}.")

    """
    Code related to hint management
    """
    def requestHints(self):
        """
        Called via an astron update when a client requests their full hint container.
        """

        avId = self.air.getAvatarIdFromSender()

        session: ArchipelagoSession = self.__getSession(avId)
        if session is None:
            return

        self.d_setHints(avId, session.getHintContainer())

    def d_setHints(self, avId, hint_container: HintContainer):
        """
        Send the full hint container to a certain client for sync purposes.
        """
        self.sendUpdateToAvatarId(avId, 'setHints', [hint_container.to_struct()])

    def d_sendHint(self, avId, hint: HintedItem):
        """
        Send a singular hint to a player for them to additively cache it locally
        """
        self.sendUpdateToAvatarId(avId, 'addHint', [hint.to_struct()])

    def d_sendHints(self, avId, hints: List[HintedItem]):
        """
        Send multiple hints to a player for them to additively cache them locally
        """
        self.sendUpdateToAvatarId(avId, 'addHints', [hint.to_struct() for hint in hints])

    """
    Boilerplate astron code throw up emoji
    """

    # No need to use, boilerplate for ram astron field
    def getSync(self):
        return self.__previousSyncedInformation

    # No need to use, boilerplate for ram astron field
    def setSync(self, infoArray: List[ArchipelagoInformation]):
        self.__previousSyncedInformation = infoArray

    # Call to sync the client with information that they need from the AI to display information correctly.
    # This can probably be optimized later but this is just to get something to work :3
    def d_sync(self, infoArray: List[ArchipelagoInformation]):
        structList: List[List[int]] = [info.struct() for info in infoArray]
        self.sendUpdate('sync', [structList])
