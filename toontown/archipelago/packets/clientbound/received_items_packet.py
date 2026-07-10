from typing import List, Tuple

from apworld.toontown import get_item_def_from_id
from toontown.archipelago.definitions.bounties import choose_bounty_replacement_item_id, get_reward_name
from toontown.archipelago.definitions.rewards import APReward, get_ap_reward_from_id, EarnedAPReward
from toontown.archipelago.util.net_utils import NetworkItem
from toontown.archipelago.packets.clientbound.clientbound_packet_base import ClientBoundPacketBase


# Sent to clients when they receive an item.
class ReceivedItemsPacket(ClientBoundPacketBase):

    def __init__(self, json_data):
        super().__init__(json_data)

        # The next empty slot in the list of items for the receiving client.
        self.index: int = json_data['index']

        # The items which the client is receiving.
        self.items: List[NetworkItem] = json_data['items']

    def handle(self, client):

        items_received: List[Tuple[int, int]] = client.av.getReceivedItems()
        av_indeces_already_received = set(item[0] for item in items_received)

        new_items: List[Tuple[int, int]] = []

        reward_index = self.index
        for item in self.items:

            # Have we already received the index of this reward?
            not_applied_yet = reward_index not in av_indeces_already_received

            # If we need to apply it go ahead and keep track on the toon that we applied this specific reward
            if not_applied_yet:
                itemName = client.get_item_name(item.item, client.get_local_slot())
                itemDef = get_item_def_from_id(item.item)
                if itemDef is not None:
                    itemName = itemDef.name.value
                fromName = client.get_slot_info(item.player).name
                if client.av.consumeTradedReceivedItem(item.item):
                    self.debug(f"Replaced traded copy of {itemName} from {fromName} with natural AP receipt")
                elif client.av.consumeBountyReceivedItem(item.item):
                    replacementItemId = choose_bounty_replacement_item_id()
                    replacementName = get_reward_name(replacementItemId)
                    replacementRewardDefinition: APReward = get_ap_reward_from_id(replacementItemId)
                    replacementReward = EarnedAPReward(
                        client.av,
                        replacementRewardDefinition,
                        reward_index,
                        replacementItemId,
                        "Bounty Board Replacement",
                        True,
                    )
                    client.av.queueAPReward(replacementReward)
                    self.debug(f"Replaced bounty copy of {itemName} from {fromName} with {replacementName}")
                    client.av.d_sendArchipelagoMessage(
                        f"Your natural {itemName} became {replacementName} because you already earned it from a bounty."
                    )
                    new_items.append((reward_index, replacementItemId))
                    reward_index += 1
                    continue
                else:
                    ap_reward_definition: APReward = get_ap_reward_from_id(item.item)
                    reward: EarnedAPReward = EarnedAPReward(client.av, ap_reward_definition, reward_index, item.item, fromName, item.player == client.slot)
                    client.av.queueAPReward(reward)
                    self.debug(f"Queued {itemName} from {fromName}")

                    # Relay a cosmetic-only notice to other AP-connected toons on the same game
                    # server so they can see this reward too. This does NOT affect their own
                    # Archipelago session, item state, or progression in any way.
                    client.av.d_broadcastAPRewardToOthers(itemName, fromName)
                new_items.append((reward_index, item.item))

            # Incrememnt the reward index and go to the next one
            reward_index += 1

        # Now perform an update on the items that this av has received
        items_received.extend(new_items)
        client.av.b_setReceivedItems(items_received)
