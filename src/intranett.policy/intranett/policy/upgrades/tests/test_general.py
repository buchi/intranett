from Acquisition import aq_parent
from plone.app.testing import login
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import TEST_USER_ID
from Products.CMFCore.utils import getToolByName

from intranett.policy.config import POLICY_PROFILE
from intranett.policy.config import THEME_PROFILE
from intranett.policy.tests.base import IntranettTestCase
from intranett.policy.upgrades import run_all_upgrades
from intranett.policy.upgrades.tests.base import FunctionalUpgradeTestCase
from intranett.policy.upgrades.tests.utils import ensure_no_addon_upgrades


class TestFullUpgrade(IntranettTestCase):

    def test_list_steps(self):
        portal = self.layer['portal']
        setup = getToolByName(portal, "portal_setup")
        upgrades = ensure_no_addon_upgrades(setup)
        for profile, steps in upgrades.items():
            self.assertEquals(len(steps), 0,
                              "Found unexpected upgrades: %s" % steps)

    def test_do_upgrades(self):
        portal = self.layer['portal']
        setup = getToolByName(portal, "portal_setup")
        setRoles(portal, TEST_USER_ID, ['Manager'])

        setup.setLastVersionForProfile(POLICY_PROFILE, '1')
        setup.setLastVersionForProfile(THEME_PROFILE, '1')

        upgrades = setup.listUpgrades(THEME_PROFILE)
        self.failUnless(len(upgrades) > 0)

        all_finished = run_all_upgrades(setup)

        # And we have reached our current profile versions
        self.assertTrue(all_finished)

        # There are no more upgrade steps available
        upgrades = setup.listUpgrades(THEME_PROFILE)
        self.failUnless(len(upgrades) == 0)

        upgrades = setup.listUpgrades(POLICY_PROFILE)
        self.failUnless(len(upgrades) == 0)


class TestFunctionalMigrations(FunctionalUpgradeTestCase):

    level = 2

    def test_gs_diff(self):
        self.importFile(__file__, 'one.zexp')
        oldsite, result = self.migrate()

        login(aq_parent(oldsite), SITE_OWNER_NAME)
        diff = self.export()
        remaining = self.parse_diff(diff)

        self.assertEquals(set(remaining.keys()), set([]),
                          "Unexpected diffs in:\n %s" % remaining.items())

    def test_list_steps_for_addons(self):
        self.importFile(__file__, 'one.zexp')
        oldsite, result = self.migrate()

        setup = getToolByName(oldsite, "portal_setup")
        upgrades = ensure_no_addon_upgrades(setup)
        for profile, steps in upgrades.items():
            self.assertEquals(len(steps), 0,
                              "Found unexpected upgrades: %s" % steps)
