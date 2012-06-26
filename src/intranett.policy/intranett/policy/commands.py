import logging
import sys
from email import message_from_string
from optparse import OptionParser

import transaction
from AccessControl.SecurityManagement import newSecurityManager
from Acquisition import aq_get
from zope.component import getUtility
from zope.site.hooks import setHooks
from zope.site.hooks import setSite

logger = logging.getLogger()


def _setup(app, site=None):
    """Set up our environment.

    Create a request, log in as admin and set the traversal hooks on the site.

    """
    from Testing import makerequest # Do not import this at the module level!
    app = makerequest.makerequest(app)

    # Login as admin
    admin = app.acl_users.getUserById('admin')
    if admin is None:
        logger.error("No user called `admin` found in the database. "
            "Use --rootpassword to create one.")
        sys.exit(1)

    # Wrap the admin in the right context; from inside the site if we have one
    if site is not None:
        admin = admin.__of__(site.acl_users)
        site = app[site.getId()]
    else:
        admin = admin.__of__(app.acl_users)
    newSecurityManager(None, admin)

    # Set up local site manager, skins and language
    if site is not None:
        setHooks()
        setSite(site)
        site.setupCurrentSkin(site.REQUEST)
        site.REQUEST['HTTP_ACCEPT_LANGUAGE'] = site.Language()

    return (app, site)


def create_site(app, args):
    # Display all messages on stderr
    logger.setLevel(logging.WARN)
    logger.handlers[0].setLevel(logging.WARN)

    parser = OptionParser()
    parser.add_option('-f', '--force', action='store_true', default=False,
        help='Force creation of a site when one already exists.')
    parser.add_option('-r', '--rootpassword', default=None,
        help='Create a admin user in the Zope root with the given password.')
    parser.add_option('-l', '--language', default='en',
        help='The language used in the new site. [default: "%default"]')
    (options, args) = parser.parse_args(args=args)

    if options.rootpassword:
        acl = app.acl_users
        users = getattr(acl, 'users', None)
        if not users:
            # Non-PAS folder from a fresh database
            app.acl_users._doAddUser('admin', options.rootpassword,
                ['Manager'], [])

    existing = app.objectIds('Plone Site')
    if existing:
        if not options.force:
            logger.error('Plone site already exists. '
                'Use --force to replace it.')
            sys.exit(1)
        else:
            for id_ in existing:
                del app[id_]
                logger.info('Removed existing Plone site %r.' % id_)
            app._p_jar.db().cacheMinimize()

    app, _ = _setup(app)

    request = app.REQUEST
    request.form = {
        'extension_ids': (
            'intranett.policy:default', 'intranett.policy:content',),
        'form.submitted': True,
        'language': options.language,
    }
    from intranett.policy.browser.admin import AddIntranettSite
    addsite = AddIntranettSite(app, request)
    addsite()

    # setup initial xmpp nodes
    from intranett.policy.setuphandlers import setup_xmpp
    existing = app.objectValues('Plone Site')
    setup_xmpp(existing[0])

    transaction.get().note('Added new Plone site.')
    transaction.get().commit()
    logger.info('Added new Plone site.')


def create_site_admin(app, args):
    # Display all messages on stderr
    logger.setLevel(logging.INFO)
    logger.handlers[0].setLevel(logging.INFO)

    existing = app.objectValues('Plone Site')
    site = existing and existing[0] or None
    if site is None:
        logger.error("No Plone site found in the database.")
        sys.exit(1)

    _, site = _setup(app, site)

    parser = OptionParser()
    parser.add_option('-l', '--login', default=None,
        help='Site admin login.')
    parser.add_option('-e', '--email', default=None,
        help='Site admin email.')
    parser.add_option('-n', '--fullname', default=None,
        help='Site admin full name.')
    parser.add_option('-a', '--hostname', default=None,
        help='Intranett site host name.')
    (options, args) = parser.parse_args(args=args)

    # User info
    login = options.login
    email = options.email
    fullname = options.fullname
    hostname = options.hostname

    if not login:
        logger.error("Missing option --login.")
        sys.exit(1)
    if not email:
        logger.error("Missing option --email.")
        sys.exit(1)
    if not fullname:
        logger.error("Missing option --fullname.")
        sys.exit(1)
    if not hostname:
        logger.error("Missing option --hostname.")
        sys.exit(1)

    # Add and notify the site admin user
    mt = aq_get(site, 'portal_membership')
    pt = aq_get(site, 'portal_password_reset')
    rt = aq_get(site, 'portal_registration')

    if mt.getMemberById(login) is not None:
        logger.error("User %s already exists." % login)
        sys.exit(1)

    from intranett.policy.browser.activation import ActivationMail

    # Get the hostname
    if not hostname.endswith('.intranett.no'):
        hostname += '.intranett.no'

    mt.addMember(login, rt.generatePassword(),
        ['Member', 'Site Administrator'], [])
    member = mt.getMemberById(login) # getMemberByLogin???
    member.setMemberProperties(dict(email=email, fullname=fullname))
    reset = pt.requestReset(login)

    # change ownership of all content to new user and update dates to now
    from intranett.policy.config import PERSONAL_FOLDER_ID
    from DateTime import DateTime
    user = member.getUser()
    userid = user.getId()
    now = DateTime()

    catalog = aq_get(site, 'portal_catalog')
    brains = catalog.unrestrictedSearchResults()
    for brain in brains:
        if brain.portal_type.startswith('Member'):
            continue
        if brain.getId == PERSONAL_FOLDER_ID:
            continue
        obj = brain.getObject()
        obj.setCreators(userid)
        obj.changeOwnership(user)
        obj.setCreationDate(now)
        obj.setEffectiveDate(now)
        obj.setModificationDate(now)
        obj.reindexObject(idxs=None)

    # Mail him
    mail_text = ActivationMail(site, site.REQUEST)(member=member,
        reset=reset, email=email, fullname=fullname, hostname=hostname)
    if isinstance(mail_text, unicode):
        mail_text = mail_text.encode('utf-8')
    mail_text = mail_text.replace('http://foo/Plone/passwordreset/',
                                  'https://%s/activate/' % hostname)

    message_obj = message_from_string(mail_text.strip())
    subject = message_obj['Subject']
    m_to = message_obj['To']
    m_from = message_obj['From']

    host = aq_get(site, 'MailHost')
    host.send(mail_text, m_to, m_from, subject=subject,
              charset='utf-8', immediate=True)

    from jarn.xmpp.core.interfaces import IAdminClient
    from jarn.xmpp.core.subscribers.startup import setupAdminClient
    from jarn.xmpp.core.subscribers.user_management import onUserCreation
    from jarn.xmpp.twisted.testing import wait_for_client_state
    from jarn.xmpp.twisted.testing import wait_on_deferred
    from jarn.xmpp.twisted.testing import wait_on_client_deferreds

    setupAdminClient(None, None)
    client = getUtility(IAdminClient)
    wait_for_client_state(client, 'authenticated')
    wait_on_client_deferreds(client)


    class FakeEvent(object):
        pass

    ev = FakeEvent()
    ev.principal = user
    d = onUserCreation(ev)
    wait_on_deferred(d)

    transaction.get().note('Added site admin user %r.' % login)
    transaction.get().commit()
    logger.info('Added site admin user %r.', login)


def upgrade(app, args):
    # Display all messages on stderr
    logger.setLevel(logging.DEBUG)
    logger.handlers[0].setLevel(logging.DEBUG)

    existing = app.objectValues('Plone Site')
    site = existing and existing[0] or None
    if site is None:
        logger.error("No Plone site found in the database.")
        sys.exit(1)

    _, site = _setup(app, site)

    from intranett.policy.config import config

    logger.info("Starting the upgrade.\n\n")
    setup = site.portal_setup
    config.run_all_upgrades(setup)
    logger.info("Ran upgrade steps.")

    # Recook resources, as some CSS/JS files might have changed.
    # TODO: We could try to determine if this is needed in some way
    site.portal_javascripts.cookResources()
    site.portal_css.cookResources()
    logger.info("Resources recooked.")

    transaction.get().note('Upgraded profiles and recooked resources.')
    transaction.get().commit()
    sys.exit(0)
