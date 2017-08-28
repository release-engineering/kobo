# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):

    def forwards(self, orm):
        db.rename_column('auth_user_groups',           'longnameuser_id', 'user_id')
        db.rename_column('auth_user_user_permissions', 'longnameuser_id', 'user_id')

    def backwards(self, orm):
        db.rename_column('auth_user_groups',           'user_id', 'longnameuser_id')
        db.rename_column('auth_user_user_permissions', 'user_id', 'longnameuser_id')
