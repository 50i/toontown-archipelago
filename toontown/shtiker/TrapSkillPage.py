from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel, DGG
from panda3d.core import TextNode

from .ShtikerPage import ShtikerPage
from toontown.archipelago.definitions.trap_skills import (TRAP_SKILLS, TREE_ORDER, TREE_POSITIONS,
                                                          TREE_SKILL_ORDER, TREE_TITLES,
                                                          spent_skill_points)
from toontown.toonbase import ToontownGlobals, TTLocalizer


class TrapSkillPage(ShtikerPage):
    def __init__(self):
        ShtikerPage.__init__(self)
        self.skillButtons = []
        self.tabButtons = []
        self.activeTree = TREE_ORDER[0]

    def load(self):
        self.title = DirectLabel(
            parent=self,
            relief=None,
            text=TTLocalizer.TrapSkillPageTitle,
            text_scale=0.12,
            text_font=ToontownGlobals.getSignFont(),
            text_fg=(0.75, 0.08, 0.05, 1),
            text_shadow=(1, 1, 1, 1),
            pos=(0, 0, 0.6),
        )
        self.panel = DirectFrame(
            parent=self,
            relief=DGG.RAISED,
            borderWidth=(0.012, 0.012),
            frameColor=(1.0, 0.95, 0.72, 1),
            frameSize=(-0.68, 0.68, -0.42, 0.43),
            pos=(0, 0, 0.02),
        )
        self.treeTitle = DirectLabel(
            parent=self.panel,
            relief=None,
            text="",
            text_scale=0.06,
            text_font=ToontownGlobals.getSignFont(),
            text_fg=(0.15, 0.1, 0.04, 1),
            textMayChange=True,
            pos=(0, 0, 0.32),
        )
        self.pointsLabel = DirectLabel(
            parent=self.panel,
            relief=None,
            text="",
            text_scale=0.045,
            text_font=ToontownGlobals.getInterfaceFont(),
            text_fg=(0.08, 0.08, 0.03, 1),
            textMayChange=True,
            pos=(0, 0, 0.25),
        )
        self._makeTabs()
        self._refresh()

    def unload(self):
        self.ignore('ap-trap-skills-updated')
        for button in self.skillButtons:
            button.destroy()
        for button in self.tabButtons:
            button.destroy()
        self.skillButtons = []
        self.tabButtons = []
        self.pointsLabel.destroy()
        self.treeTitle.destroy()
        self.panel.destroy()
        self.title.destroy()
        ShtikerPage.unload(self)

    def enter(self):
        ShtikerPage.enter(self)
        self.accept('ap-trap-skills-updated', self._refresh)
        self._refresh()

    def exit(self):
        self.ignore('ap-trap-skills-updated')
        ShtikerPage.exit(self)

    def _makeTabs(self):
        guiButton = loader.loadModel('phase_3/models/gui/quit_button')
        startX = -0.45
        for index, tree in enumerate(TREE_ORDER):
            button = DirectButton(
                parent=self,
                relief=None,
                image=(
                    guiButton.find('**/QuitBtn_UP'),
                    guiButton.find('**/QuitBtn_DN'),
                    guiButton.find('**/QuitBtn_RLVR')
                ),
                image_scale=(0.52, 1, 0.72),
                text=TREE_TITLES[tree],
                text_scale=0.034,
                text_fg=(0.05, 0.035, 0.0, 1),
                text_pos=(0, -0.01),
                pos=(startX + (index * 0.3), 0, 0.46),
                command=self._setTree,
                extraArgs=[tree],
            )
            self.tabButtons.append(button)

    def _setTree(self, tree):
        self.activeTree = tree
        self._refresh()

    def _canUnlockSkill(self, skillId, unlocked, available):
        skill = TRAP_SKILLS[skillId]
        if skillId in unlocked:
            return False
        if any(required not in unlocked for required in skill.requires):
            return False
        if any(locked in unlocked for locked in skill.locks):
            return False
        return available >= skill.cost

    def _skillStateText(self, skillId, unlocked, available):
        skill = TRAP_SKILLS[skillId]
        if skillId in unlocked:
            return "In Pool" if skill.trap_item_ids else "Passive"
        if any(locked in unlocked for locked in skill.locks):
            return "Locked"
        if any(required not in unlocked for required in skill.requires):
            return f"{skill.cost} Blue Glue"
        if available < skill.cost:
            return f"{skill.cost} Blue Glue"
        return f"Unlock {skill.cost}"

    def _textColor(self, skillId, unlocked):
        if skillId in unlocked:
            return (0.0, 0.28, 0.0, 1)
        if any(locked in unlocked for locked in TRAP_SKILLS[skillId].locks):
            return (0.45, 0.0, 0.0, 1)
        return (0.0, 0.0, 0.0, 1)

    def _refresh(self):
        for button in self.skillButtons:
            button.destroy()
        self.skillButtons = []

        av = getattr(base, 'localAvatar', None)
        unlocked = set(av.getTrapSkills()) if av is not None and hasattr(av, 'getTrapSkills') else set()
        total = av.getTrapSkillPoints() if av is not None and hasattr(av, 'getTrapSkillPoints') else 0
        available = max(0, total - spent_skill_points(unlocked))
        self.pointsLabel['text'] = f"Blue Glue Sticks: {available}/{total}"
        self.treeTitle['text'] = f"{TREE_TITLES[self.activeTree]} Skill Tree"

        for tree, tab in zip(TREE_ORDER, self.tabButtons):
            tab['text_fg'] = (0.0, 0.22, 0.0, 1) if tree == self.activeTree else (0.05, 0.035, 0.0, 1)

        positions = TREE_POSITIONS[self.activeTree]
        for skillId in TREE_SKILL_ORDER[self.activeTree]:
            skill = TRAP_SKILLS[skillId]
            x, z = positions[skillId]
            canUnlock = self._canUnlockSkill(skillId, unlocked, available)
            button = DirectButton(
                parent=self.panel,
                relief=DGG.RAISED,
                borderWidth=(0.01, 0.01),
                frameColor=(1.0, 0.86, 0.12, 1),
                text=f"{skill.name}\n{self._skillStateText(skillId, unlocked, available)}",
                text_fg=self._textColor(skillId, unlocked),
                text_font=ToontownGlobals.getInterfaceFont(),
                text_scale=0.031,
                text_wordwrap=8.2,
                text_align=TextNode.ACenter,
                text_pos=(0, -0.024),
                frameSize=(-0.17, 0.17, -0.075, 0.075),
                pos=(x, 0, z),
                command=self._unlockSkill,
                extraArgs=[skillId],
                state=DGG.NORMAL if canUnlock else DGG.DISABLED,
            )
            self.skillButtons.append(button)

    def _unlockSkill(self, skillId):
        if hasattr(base, 'localAvatar'):
            base.localAvatar.d_unlockTrapSkill(skillId)
