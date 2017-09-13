# coding: utf-8
import os
import MySQLdb as mdb
import json
import operator
from contextlib import closing
from warnings import filterwarnings
from wikitools import wiki, api
import re
import datetime
filterwarnings('ignore', category=mdb.Warning)

script_dir = os.path.dirname(__file__)
archived_url_path = os.path.join(script_dir, 'archived_urls.json')
article_to_pageid_path = os.path.join(script_dir, 'article_to_pageid.json')
open_comment_path = os.path.join(script_dir, "open_comments.json")
title_path = os.path.join(script_dir, "original_titles.json")
save_path = os.path.join(script_dir, 'stored_revs.json')
print title_path


#archived_urls, open_comments, article_to_pageid
with open(archived_url_path) as file:
    archived_urls = json.load(file)

with open(open_comment_path) as file:
    open_comments = json.load(file)

with open(article_to_pageid_path) as file:
    article_to_pageid = json.load(file)


def load_json(file_path):
    with open(file_path) as file:
        blob = json.load(file)
    return blob


def dump_json(blob, file_path):
    with open(file_path, 'w') as file:
        json.dump(blob, file)

class DB():
    def __init__(self, host, user, passwd, db):
        try:
            self.conn = mdb.connect(host= host, user=user, passwd = passwd, db=db)
            self.conn.set_character_set('utf8')

        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def store_anonymous_id(self):
        command = "select id from website_commentauthor where disqus_id= %s and is_wikipedia = %s"
        comment_author_id = self.fetch_one(command, ('anonymous', 1))
        return comment_author_id

    def get_anonymous_id(self):
        return self.anonymous_id

    def store_wiki_source_id(self):
        cmd = 'select id from website_source where source_name = %s'
        (source_id,) = self.fetch_one(cmd, ("Wikipedia Talk Page",))
        return source_id

    def get_wiki_source_id(self):
        return self.wiki_source_id

    def fetch_one(self, cmd, params):
        with closing(self.conn.cursor()) as cur:
            cur.execute('SET NAMES utf8;')
            cur.execute('SET CHARACTER SET utf8;')
            cur.execute('SET character_set_connection=utf8;')
            cur.execute(cmd, params)
            result = cur.fetchone()
            if result:
                return result
            return None

    def fetch_all(self, cmd, params):
        with closing(self.conn.cursor()) as cur:
            cur.execute('SET NAMES utf8;')
            cur.execute('SET CHARACTER SET utf8;')
            cur.execute('SET character_set_connection=utf8;')
            cur.execute(cmd, params)
            rows = cur.fetchall()
            return rows

    def insert(self, cmd, params):
        with closing(self.conn.cursor()) as cur:
            cur.execute('SET NAMES utf8;')
            cur.execute('SET CHARACTER SET utf8;')
            cur.execute('SET character_set_connection=utf8;')
            cur.execute(cmd, params)
            self.conn.commit()
            return cur.lastrowid

    def update(self, command, params):
        with closing(self.conn.cursor()) as cur:
            cur.execute('SET NAMES utf8;')
            cur.execute('SET CHARACTER SET utf8;')
            cur.execute('SET character_set_connection=utf8;')
            cur.execute(command, params)
            self.conn.commit()
            return cur.lastrowid


    def close(self):
        self.conn.close()




def extract_revision_info(results, revs):
    for res in results:
        id = res['revid']
        if 'user' in res:
            user = res['user']
        if 'timestamp' in res:
            timestamp = res['timestamp']
        revs[id] = (user, timestamp)
    return revs


def get_all_revisions(title, date, rvcontinue, page_revisions):
    params = {'action': 'query', 'prop': 'revisions','titles': title, 'rvlimit':500,
              'rvprop':'ids|user|timestamp', 'redirects':'yes', 'rvstart':date,
              'format':'json' }
    if rvcontinue != "":
        params["rvcontinue"] = rvcontinue
    try:
        request = api.APIRequest(site, params)
        all_result = request.query()

        query_result = all_result["query"]["pages"].values()[0]
    #     print all_result
        if "revisions" in query_result:
            revision_results = query_result["revisions"]
            page_revisions = extract_revision_info(revision_results, page_revisions)
        if "continue" in all_result:
            revcon_param = all_result["continue"]["rvcontinue"]
            return get_all_revisions(title, date, revcon_param, page_revisions)
        else:
            return page_revisions
    except api.APIError:
        pass


def get_original_title(archive_pageid):
    # find the title
    params = {'action': 'query','pageids': archive_pageid,
              'redirects':'yes', 'format':'json' }
    request = api.APIRequest(site, params)
    all_result = request.query()
    title = all_result["query"]["pages"][archive_pageid]["title"]
    original_title = title.split("/Archive")[0]
    return original_title


site = wiki.Wiki('https://en.wikipedia.org/w/api.php?')


def get_revs_from_archives(archived_urls, open_comments, article_to_pageid, store_revs):
    count = 0
    stored_revs = {}
    stored_titles = {}
    # with open(save_path) as file:
    #     stored_revs = json.load(file)
    with open(title_path) as file:
        stored_titles = json.load(file)

    for arch_id in archived_urls:
        if arch_id not in stored_titles.keys():
            count += 1
            original_title = get_original_title(article_to_pageid[str(arch_id)])
            stored_titles[arch_id] = original_title

            if str(arch_id) in open_comments:
                opendate = open_comments[str(arch_id)]
                store_revs[arch_id] =  get_all_revisions(original_title, opendate, "", {})
                print 'stored' + str(arch_id)
            print arch_id

            if count % 5 == 0:
                with open(os.path.join(script_dir, 'stored_revs_'+arch_id+'.json'), "w") as file:
                    json.dump(store_revs, file)
                with open(title_path, 'w') as file:
                    json.dump(stored_titles, file)

    with open(save_path, "w") as file:
        json.dump(store_revs, file)
    with open(title_path, 'w') as file:
        json.dump(stored_titles, file)
    return stored_titles, store_revs
