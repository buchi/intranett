from Products.CMFCore.utils import getToolByName
import transaction
from zExceptions import Unauthorized

from intranett.policy.tests.base import get_browser
from intranett.policy.tests.base import IntranettFunctionalTestCase


class TestWorkflow(IntranettFunctionalTestCase):

    def setUp(self):
        portal = self.layer['portal']
        self.folder = portal['test-folder']
        projectroom_id = self.folder.invokeFactory('ProjectRoom', 'projectroom')
        self.projectroom = self.folder[projectroom_id]
        self.wf = portal.portal_workflow
        self.catalog = portal.portal_catalog

    def checkCatalog(self, container, id, state):
        # Object should be findable in catalog
        path='/'.join(container.getPhysicalPath())
        brains = self.catalog(path=path, getId=id, review_state=state)
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].getId, id)

    def checkOwner(self, context):
        # Owner role should have permissions
        perms = context.permissionsOfRole('Owner')
        perms = sorted(x['name'] for x in perms if x['selected'])
        expected = ['Access contents information', 'Modify portal content', 'View']
        if getattr(context, 'isPrincipiaFolderish', None):
            expected.insert(1, 'Change portal events')
        self.assertEqual(perms, expected)

    def checkNoOwner(self, context):
        # Owner role should not have permissions
        perms = context.permissionsOfRole('Owner')
        perms = sorted(x['name'] for x in perms if x['selected'])
        self.assertEqual(perms, [])

    def test_new_projectroom_is_private(self):
        portal = self.layer['portal']
        getInfoFor = self.wf.getInfoFor
        self.assertEqual(getInfoFor(self.projectroom, 'review_state'), 'private')
        self.checkCatalog(portal, 'projectroom', 'private')
        self.checkOwner(self.projectroom)

    def test_published_projectroom_is_published(self):
        portal = self.layer['portal']
        getInfoFor = self.wf.getInfoFor
        self.wf.doActionFor(self.projectroom, "publish")
        self.assertEqual(getInfoFor(self.projectroom, 'review_state'), 'published')
        self.checkCatalog(portal, 'projectroom', 'published')
        self.checkOwner(self.projectroom)

    def test_rehidden_projectroom_is_private(self):
        portal = self.layer['portal']
        getInfoFor = self.wf.getInfoFor
        self.wf.doActionFor(self.projectroom, "publish")
        self.wf.doActionFor(self.projectroom, "hide")
        self.assertEqual(getInfoFor(self.projectroom, 'review_state'), 'private')
        self.checkCatalog(portal, 'projectroom', 'private')
        self.checkOwner(self.projectroom)

    def test_existing_content_in_projectroom_is_protected_on_hiding(self):
        getInfoFor = self.wf.getInfoFor
        self.wf.doActionFor(self.projectroom, "publish")
        link_id = self.projectroom.invokeFactory("Link", "link")
        doc_id = self.projectroom.invokeFactory("Document", "doc")
        file_id = self.projectroom.invokeFactory("File", "file")
        self.checkNoOwner(self.projectroom[link_id])
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])
        self.wf.doActionFor(self.projectroom, "hide")
        self.assertEqual(getInfoFor(self.projectroom[link_id], 'review_state'), 'protected')
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'protected')
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'protected')
        self.checkCatalog(self.projectroom, link_id, 'protected')
        self.checkCatalog(self.projectroom, doc_id, 'protected')
        self.checkCatalog(self.projectroom, file_id, 'protected')
        self.checkNoOwner(self.projectroom[link_id])
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])

    def test_existing_content_in_projectroom_is_unprotected_on_publishing(self):
        getInfoFor = self.wf.getInfoFor
        link_id = self.projectroom.invokeFactory("Link", "link")
        doc_id = self.projectroom.invokeFactory("Document", "doc")
        file_id = self.projectroom.invokeFactory("File", "file")
        self.checkNoOwner(self.projectroom[link_id])
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])
        self.wf.doActionFor(self.projectroom, "publish")
        self.assertEqual(getInfoFor(self.projectroom[link_id], 'review_state'), 'published')
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'published')
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'published')
        self.checkCatalog(self.projectroom, link_id, 'published')
        self.checkCatalog(self.projectroom, doc_id, 'published')
        self.checkCatalog(self.projectroom, file_id, 'published')
        self.checkNoOwner(self.projectroom[link_id])
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])

    def test_new_content_in_private_projectroom_is_protected(self):
        getInfoFor = self.wf.getInfoFor
        link_id = self.projectroom.invokeFactory("Link", "link")
        doc_id = self.projectroom.invokeFactory("Document", "doc")
        file_id = self.projectroom.invokeFactory("File", "file")
        self.checkNoOwner(self.projectroom[link_id])
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])
        self.assertEqual(getInfoFor(self.projectroom[link_id], 'review_state'), 'protected')
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'protected')
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'protected')
        self.checkCatalog(self.projectroom, link_id, 'protected')
        self.checkCatalog(self.projectroom, doc_id, 'protected')
        self.checkCatalog(self.projectroom, file_id, 'protected')
        self.checkNoOwner(self.projectroom[link_id])
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])

    def test_new_content_in_public_projectroom_is_unprotected(self):
        getInfoFor = self.wf.getInfoFor
        self.wf.doActionFor(self.projectroom, "publish")
        link_id = self.projectroom.invokeFactory("Link", "link")
        doc_id = self.projectroom.invokeFactory("Document", "doc")
        file_id = self.projectroom.invokeFactory("File", "file")
        self.checkNoOwner(self.projectroom[link_id])
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])
        self.assertEqual(getInfoFor(self.projectroom[link_id], 'review_state'), 'published')
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'published')
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'published')
        self.checkCatalog(self.projectroom, link_id, 'published')
        self.checkCatalog(self.projectroom, doc_id, 'published')
        self.checkCatalog(self.projectroom, file_id, 'published')
        self.checkNoOwner(self.projectroom[link_id])
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])

    def test_copypasted_content_in_private_projectroom_is_protected(self):
        getInfoFor = self.wf.getInfoFor
        doc_id = self.folder.invokeFactory("Document", "doc")
        file_id = self.folder.invokeFactory("File", "file")
        self.checkOwner(self.folder[doc_id])
        self.checkOwner(self.folder[file_id])
        transaction.savepoint(True)
        cb = self.folder.manage_copyObjects(['doc', 'file'])
        self.projectroom.manage_pasteObjects(cb)
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'protected')
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'protected')
        self.checkCatalog(self.projectroom, doc_id, 'protected')
        self.checkCatalog(self.projectroom, file_id, 'protected')
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])

    def test_copypasted_content_in_public_projectroom_is_unprotected(self):
        getInfoFor = self.wf.getInfoFor
        self.wf.doActionFor(self.projectroom, "publish")
        doc_id = self.folder.invokeFactory("Document", "doc")
        file_id = self.folder.invokeFactory("File", "file")
        self.checkOwner(self.folder[doc_id])
        self.checkOwner(self.folder[file_id])
        transaction.savepoint(True)
        cb = self.folder.manage_copyObjects(['doc', 'file'])
        self.projectroom.manage_pasteObjects(cb)
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'published')
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'published')
        self.checkCatalog(self.projectroom, doc_id, 'published')
        self.checkCatalog(self.projectroom, file_id, 'published')
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])

    def test_cutpasted_content_in_private_projectroom_is_protected(self):
        getInfoFor = self.wf.getInfoFor
        doc_id = self.folder.invokeFactory("Document", "doc")
        file_id = self.folder.invokeFactory("File", "file")
        self.checkOwner(self.folder[doc_id])
        self.checkOwner(self.folder[file_id])
        transaction.savepoint(True)
        cb = self.folder.manage_copyObjects(['doc', 'file'])
        self.projectroom.manage_pasteObjects(cb)
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'protected')
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'protected')
        self.checkCatalog(self.projectroom, doc_id, 'protected')
        self.checkCatalog(self.projectroom, file_id, 'protected')
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])

    def test_cutpasted_content_in_public_projectroom_is_unprotected(self):
        getInfoFor = self.wf.getInfoFor
        self.wf.doActionFor(self.projectroom, "publish")
        doc_id = self.folder.invokeFactory("Document", "doc")
        file_id = self.folder.invokeFactory("File", "file")
        self.checkOwner(self.folder[doc_id])
        self.checkOwner(self.folder[file_id])
        transaction.savepoint(True)
        cb = self.folder.manage_copyObjects(['doc', 'file'])
        self.projectroom.manage_pasteObjects(cb)
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'published')
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'published')
        self.checkCatalog(self.projectroom, doc_id, 'published')
        self.checkCatalog(self.projectroom, file_id, 'published')
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])

    def test_renamed_content_in_private_projectroom_remains_protected(self):
        getInfoFor = self.wf.getInfoFor
        doc_id = self.projectroom.invokeFactory("Document", "doc")
        file_id = self.projectroom.invokeFactory("File", "file")
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])
        transaction.savepoint(True)
        self.projectroom.manage_renameObject(doc_id, 'doc1')
        self.projectroom.manage_renameObject(file_id, 'file1')
        self.assertEqual(getInfoFor(self.projectroom['doc1'], 'review_state'), 'protected')
        self.assertEqual(getInfoFor(self.projectroom['file1'], 'review_state'), 'protected')
        self.checkCatalog(self.projectroom, 'doc1', 'protected')
        self.checkCatalog(self.projectroom, 'file1', 'protected')
        self.checkNoOwner(self.projectroom['doc1'])
        self.checkNoOwner(self.projectroom['file1'])

    def test_renamed_content_in_public_projectroom_remains_unprotected(self):
        getInfoFor = self.wf.getInfoFor
        self.wf.doActionFor(self.projectroom, "publish")
        doc_id = self.projectroom.invokeFactory("Document", "doc")
        file_id = self.projectroom.invokeFactory("File", "file")
        self.checkNoOwner(self.projectroom[doc_id])
        self.checkNoOwner(self.projectroom[file_id])
        transaction.savepoint(True)
        self.projectroom.manage_renameObject(doc_id, 'doc1')
        self.projectroom.manage_renameObject(file_id, 'file1')
        self.assertEqual(getInfoFor(self.projectroom['doc1'], 'review_state'), 'published')
        self.assertEqual(getInfoFor(self.projectroom['file1'], 'review_state'), 'published')
        self.checkCatalog(self.projectroom, 'doc1', 'published')
        self.checkCatalog(self.projectroom, 'file1', 'published')
        self.checkNoOwner(self.projectroom['doc1'])
        self.checkNoOwner(self.projectroom['file1'])

    def test_content_cutpasted_from_private_projectroom_to_outside_is_private(self):
        getInfoFor = self.wf.getInfoFor
        doc_id = self.projectroom.invokeFactory("Document", "doc")
        self.checkNoOwner(self.projectroom[doc_id])
        transaction.savepoint(True)
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'protected')
        self.checkCatalog(self.projectroom, doc_id, 'protected')
        cb = self.projectroom.manage_cutObjects(doc_id)
        self.folder.manage_pasteObjects(cb)
        self.assertEqual(getInfoFor(self.folder[doc_id], 'review_state'), 'private')
        self.checkCatalog(self.folder, doc_id, 'private')
        self.checkOwner(self.folder[doc_id])

    def test_content_cutpasted_from_public_projectroom_to_outside_is_private(self):
        getInfoFor = self.wf.getInfoFor
        self.wf.doActionFor(self.projectroom, "publish")
        doc_id = self.projectroom.invokeFactory("Document", "doc")
        self.checkNoOwner(self.projectroom[doc_id])
        transaction.savepoint(True)
        self.assertEqual(getInfoFor(self.projectroom[doc_id], 'review_state'), 'published')
        self.checkCatalog(self.projectroom, doc_id, 'published')
        cb = self.projectroom.manage_cutObjects(doc_id)
        self.folder.manage_pasteObjects(cb)
        self.assertEqual(getInfoFor(self.folder[doc_id], 'review_state'), 'private')
        self.checkCatalog(self.folder, doc_id, 'private')
        self.checkOwner(self.folder[doc_id])

    def test_file_cutpasted_from_private_projectroom_to_outside_is_published(self):
        getInfoFor = self.wf.getInfoFor
        file_id = self.projectroom.invokeFactory("File", "file")
        self.checkNoOwner(self.projectroom[file_id])
        transaction.savepoint(True)
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'protected')
        self.checkCatalog(self.projectroom, file_id, 'protected')
        cb = self.projectroom.manage_cutObjects(file_id)
        self.folder.manage_pasteObjects(cb)
        self.assertEqual(getInfoFor(self.folder[file_id], 'review_state'), 'published')
        self.checkCatalog(self.folder, file_id, 'published')
        self.checkOwner(self.folder[file_id])

    def test_file_cutpasted_from_public_projectroom_to_outside_is_published(self):
        getInfoFor = self.wf.getInfoFor
        self.wf.doActionFor(self.projectroom, "publish")
        file_id = self.projectroom.invokeFactory("File", "file")
        self.checkNoOwner(self.projectroom[file_id])
        transaction.savepoint(True)
        self.assertEqual(getInfoFor(self.projectroom[file_id], 'review_state'), 'published')
        self.checkCatalog(self.projectroom, file_id, 'published')
        cb = self.projectroom.manage_cutObjects(file_id)
        self.folder.manage_pasteObjects(cb)
        self.assertEqual(getInfoFor(self.folder[file_id], 'review_state'), 'published')
        self.checkCatalog(self.folder, file_id, 'published')
        self.checkOwner(self.folder[file_id])


class TestProjectRooms(IntranettFunctionalTestCase):

    def test_create_projectroom(self):
        portal = self.layer['portal']
        folder = portal['test-folder']

        folder.invokeFactory('ProjectRoom', 'projectroom')

    def test_projectroom_creator_can_view_projectroom(self):
        portal = self.layer['portal']
        folder = portal['test-folder']
        wt = getToolByName(portal, 'portal_workflow')

        projectroom_id = folder.invokeFactory('ProjectRoom', 'projectroom')
        projectroom = folder[projectroom_id]
        wt.doActionFor(projectroom, 'publish')
        transaction.commit()

        browser = get_browser(self.layer['app'], loggedIn=True)
        browser.open(projectroom.absolute_url())

    def test_projectroom_creator_can_add_participants(self):
        portal = self.layer['portal']
        folder = portal['test-folder']
        wt = getToolByName(portal, 'portal_workflow')

        projectroom_id = folder.invokeFactory('ProjectRoom', 'projectroom', title="ProjectRoom", description="ws")
        projectroom = folder[projectroom_id]
        wt.doActionFor(projectroom, 'publish')
        acl_users = getToolByName(portal, 'acl_users')
        acl_users.userFolderAddUser('participant1', 'secret', ['Member'], [])
        transaction.commit()

        browser = get_browser(self.layer['app'], loggedIn=True)
        browser.handleErrors = False
        browser.open(projectroom.absolute_url()+"/edit")
        browser.getControl(name="participants:list").value = ["participant1"]
        browser.getControl("Lagre").click()
        self.assertIn("participant1", projectroom.participants)

    def test_participants_shown_on_projectroom_home(self):
        portal = self.layer['portal']
        folder = portal['test-folder']
        wt = getToolByName(portal, 'portal_workflow')

        projectroom_id = folder.invokeFactory('ProjectRoom', 'projectroom')
        projectroom = folder[projectroom_id]
        wt.doActionFor(projectroom, 'publish')

        acl_users = getToolByName(portal, 'acl_users')
        acl_users.userFolderAddUser('participant1', 'secret', ['Member'], [])
        portal.portal_membership.getMemberById("participant1").setMemberProperties({"fullname": "Max Mustermann", })
        projectroom.participants = ('participant1', )
        transaction.commit()

        browser = get_browser(self.layer['app'], loggedIn=True)
        browser.handleErrors = False
        browser.open(projectroom.absolute_url())
        self.assertTrue("Max Mustermann" in browser.contents)

    def test_participants_can_add_content_in_projectroom(self):
        portal = self.layer['portal']
        folder = portal['test-folder']
        wt = getToolByName(portal, 'portal_workflow')

        projectroom_id = folder.invokeFactory('ProjectRoom', 'projectroom')
        projectroom = folder[projectroom_id]
        wt.doActionFor(projectroom, 'publish')

        acl_users = getToolByName(portal, 'acl_users')
        acl_users.userFolderAddUser('participant1', 'secret', ['Member'], [])
        projectroom.participants = ('participant1', )
        transaction.commit()

        browser = get_browser(self.layer['app'], loggedIn=False)
        auth = 'Basic %s:%s' % ('participant1', 'secret')
        browser.addHeader('Authorization', auth)
        browser.handleErrors = False
        browser.open(projectroom.absolute_url())
        browser.getLink(id="document").click()
        browser.getControl(name="title").value="Qwertyuiop"
        browser.getControl(name="text").value="qazxswedc"
        browser.getControl("Lagre").click()

    def test_participants_shown_on_subcontent_of_projectroom(self):
        portal = self.layer['portal']
        folder = portal['test-folder']
        wt = getToolByName(portal, 'portal_workflow')

        projectroom_id = folder.invokeFactory('ProjectRoom', 'projectroom')
        projectroom = folder[projectroom_id]
        doc_id = projectroom.invokeFactory("Document", "contact")
        doc = projectroom[doc_id]
        wt.doActionFor(projectroom, 'publish')

        acl_users = getToolByName(portal, 'acl_users')
        acl_users.userFolderAddUser('participant1', 'secret', ['Member'], [])
        portal.portal_membership.getMemberById("participant1").setMemberProperties({"fullname": "Max Mustermann", })
        projectroom.participants = ('participant1', )
        transaction.commit()

        browser = get_browser(self.layer['app'], loggedIn=True)
        browser.handleErrors = False
        browser.open(doc.absolute_url())
        self.assertTrue("Max Mustermann" in browser.contents)

    def test_non_participants_can_see_public_projectroom_content(self):
        portal = self.layer['portal']
        folder = portal['test-folder']
        wt = getToolByName(portal, 'portal_workflow')

        projectroom_id = folder.invokeFactory('ProjectRoom', 'projectroom')
        projectroom = folder[projectroom_id]
        document_id = projectroom.invokeFactory("Document", "qwertyuiop")
        document = projectroom[document_id]
        wt.doActionFor(projectroom, 'publish')

        acl_users = getToolByName(portal, 'acl_users')
        acl_users.userFolderAddUser('nonparticipant', 'secret', ['Member'], [])
        transaction.commit()

        browser = get_browser(self.layer['app'], loggedIn=False)
        auth = 'Basic %s:%s' % ('nonparticipant', 'secret')
        browser.addHeader('Authorization', auth)
        browser.handleErrors = False
        browser.open(document.absolute_url())

    def test_non_participants_cannot_see_private_projectroom_in_navigation(self):
        portal = self.layer['portal']
        folder = portal['test-folder']
        wt = getToolByName(portal, 'portal_workflow')
        wt.doActionFor(folder, "publish")

        projectroom_id = folder.invokeFactory('ProjectRoom', 'wibblewobblewoo', title="wibblewobblewoo")
        projectroom = folder[projectroom_id]

        acl_users = getToolByName(portal, 'acl_users')
        acl_users.userFolderAddUser('nonparticipant', 'secret', ['Member'], [])
        transaction.commit()

        browser = get_browser(self.layer['app'], loggedIn=False)
        auth = 'Basic %s:%s' % ('nonparticipant', 'secret')
        browser.addHeader('Authorization', auth)
        browser.handleErrors = False
        browser.open(folder.absolute_url())
        self.assertFalse("wibblewobblewoo" in browser.contents)

        # We then make it public
        wt.doActionFor(projectroom, 'publish')
        transaction.commit()

        browser.open(folder.absolute_url())
        self.assertTrue("wibblewobblewoo" in browser.contents)

    def test_owner_of_protected_content_in_projectroom_cannot_see_it_when_not_a_participant(self):
        portal = self.layer['portal']
        folder = portal['test-folder']

        projectroom_id = folder.invokeFactory('ProjectRoom', 'projectroom')
        projectroom = folder[projectroom_id]
        document_id = projectroom.invokeFactory("Document", "qwertyuiop")
        document = projectroom[document_id]

        acl_users = getToolByName(portal, 'acl_users')
        acl_users.userFolderAddUser('nonparticipant', 'secret', ['Member'], [])
        document.manage_setLocalRoles('nonparticipant', ["Owner"])
        transaction.commit()

        browser = get_browser(self.layer['app'], loggedIn=False)
        auth = 'Basic %s:%s' % ('nonparticipant', 'secret')
        browser.addHeader('Authorization', auth)
        browser.handleErrors = False
        with self.assertRaises(Unauthorized):
            browser.open(document.absolute_url())

    def test_owner_of_published_content_in_projectroom_cannot_edit_it_when_not_a_participant(self):
        portal = self.layer['portal']
        folder = portal['test-folder']
        wt = getToolByName(portal, 'portal_workflow')

        projectroom_id = folder.invokeFactory('ProjectRoom', 'projectroom')
        projectroom = folder[projectroom_id]
        document_id = projectroom.invokeFactory("Document", "qwertyuiop")
        document = projectroom[document_id]
        wt.doActionFor(projectroom, 'publish')

        acl_users = getToolByName(portal, 'acl_users')
        acl_users.userFolderAddUser('nonparticipant', 'secret', ['Member'], [])
        document.manage_setLocalRoles('nonparticipant', ["Owner"])
        transaction.commit()

        browser = get_browser(self.layer['app'], loggedIn=False)
        auth = 'Basic %s:%s' % ('nonparticipant', 'secret')
        browser.addHeader('Authorization', auth)
        browser.handleErrors = False
        with self.assertRaises(Unauthorized):
            browser.open(document.absolute_url()+'/edit')

