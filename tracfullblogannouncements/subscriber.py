from trac.core import *
from trac.config import BoolOption
from announcerplugin.api import IAnnouncementSubscriber, istrue
from announcerplugin.api import IAnnouncementPreferenceProvider

class BlogSubscriber(Component):
    implements(IAnnouncementSubscriber, IAnnouncementPreferenceProvider)

    always_notify_author = BoolOption('fullblog-announcement', 
            'always_notify_author', 'true', doc="""Notify the blog author
            of any changes to her blogs, including changes to comments.""")

    def get_subscription_realms(self):
        yield 'blog'
    
    def get_subscription_categories(self, realm):
        if realm == "blog":
            yield 'post created'
            yield 'post changed'
            yield 'post deleted'
            yield 'comment created'
            yield 'comment changed'
            yield 'comment deleted'
    
    def get_subscriptions_for_event(self, event):
        if event.realm == 'blog':
            if event.category.startswith('post'):
                for user, authed, rule in self._members('post', event):
                    self.log.debug("BlogSubscriber added '%s (%s)' for '%s'"%(
                            user, authed, rule))
                    yield ("email", user, authed, None)
            else:
                for user, authed, rule in self._members('comment', event):
                    self.log.debug("BlogSubscriber added '%s (%s)' for '%s'"%(
                            user, authed, rule))
                    yield ("email", user, authed, None)

    def _members(self, type, event):
        name = event.blog_post.name
        db = self.env.get_db_cnx()
        cursor = db.cursor()

        #  My Posts
        cursor.execute("""
            SELECT value, authenticated
              FROM session_attribute 
             WHERE name='announcer_blog_my_posts'
               AND sid='%s'
        """, (event.blog_post.author,))
        result = cursor.fetchone()
        if (result and istrue(result[0])) or self.always_notify_author:
            yield (
                event.blog_post.author, 
                result and istrue(result[1]) or None,
                'My Post Subscription'
            )

        if event.category is 'post created':
            # New Posts
            cursor.execute("""
                SELECT sid, authenticated
                  FROM session_attribute 
                 WHERE name='announcer_blog_new_posts'
                   AND value='1'
            """)
            for result in cursor.fetchall():
                yield (result[0], istrue(result[1]), 'New Blog Subscription')

            # Watched Author Posts
            cursor.execute("""
                SELECT sid, authenticated, value
                  FROM session_attribute 
                 WHERE name='announcer_blog_author_posts'
            """, (event.blog_post.author,))
            for result in cursor.fetchall():
                for name in [i.strip() for i in result[2].split(',')]:
                    if name == event.blog_post.author:
                        yield (
                            result[0], 
                            istrue(result[1]), 
                            'Blog Author Subscription'
                        )

        # All
        cursor.execute("""
            SELECT sid, authenticated
              FROM session_attribute 
             WHERE name='announcer_blog_all'
               AND value='1'
        """)
        for result in cursor.fetchall():
            yield (result[0], istrue(result[1]), 'All Blog Subscription')

    def get_announcement_preference_boxes(self, req):
        if req.authname == "anonymous" and 'email' not in req.session:
            return
        yield "blog", "Blog Subscriptions"
        
    def render_announcement_preference_box(self, req, panel):
        sess = req.session
        if req.method == "POST":
            for option in ('my_posts', 'new_posts', 'all'):
                if req.args.get('announcer_blog_%s'%option):
                    sess['announcer_blog_%s'%option] = '1'
                else:
                    del sess['announcer_blog_%s'%option]
            authors = req.args.get('announcer_blog_authors')
            if len(authors.strip()):
                sess['announcer_blog_author_posts'] = authors
            else:
                del sess['announcer_blog_author_posts']
                
        data = dict(
            announcer_blog_my_posts = 1,
            announcer_blog_new_posts = 1,
            announcer_blog_all = 1,
            announcer_blog_author_posts = ''
        )
        return "prefs_announcer_blog.html", dict(data=data)

