# -*- coding: utf-8 -*-
from collective.volto.formsupport.interfaces import IFormDataStore
from datetime import datetime
from plone.dexterity.interfaces import IDexterityContent
from plone.restapi.deserializer import json_body
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from souper.interfaces import ICatalogFactory
from souper.soup import get_soup
from souper.soup import NodeAttributeIndexer
from souper.soup import Record
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface

import logging

logger = logging.getLogger(__name__)


@implementer(ICatalogFactory)
class FormDataSoupCatalogFactory(object):
    def __call__(self, context):
        #  do not set any index here..maybe on each form
        catalog = Catalog()
        block_id_indexer = NodeAttributeIndexer("block_id")
        catalog[u"block_id"] = CatalogFieldIndex(block_id_indexer)
        return catalog


@implementer(IFormDataStore)
@adapter(IDexterityContent, Interface)
class FormDataStore(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def soup(self):
        return get_soup("form_data", self.context)

    @property
    def block_id(self):
        data = json_body(self.request)
        if not data:
            data = self.request.form
        return data.get("block_id", "")

    def get_form_fields(self):
        blocks = getattr(self.context, "blocks", {})
        if not blocks:
            return {}
        form_block = {}
        for id, block in blocks.items():
            if id != self.block_id:
                continue
            block_type = block.get("@type", "")
            if block_type == "form":
                form_block = block
        if not form_block:
            return {}
        return {
            "ids": [
                x.get("field_id", "") for x in form_block.get("subblocks", [])
            ],
            "fields": form_block.get("subblocks", []),
        }

    def add(self, data):
        form_fields = self.get_form_fields()
        if not form_fields:
            logger.error(
                'Block with id {} and type "form" not found in context: {}.'.format(
                    self.block_id, self.context.absolute_url()
                )
            )
            return None

        record = Record()
        for field in data:
            key = field.get("field_id", "")
            value = field.get("value", "")
            if key in form_fields["ids"]:
                record.attrs[key] = value
        record.attrs["date"] = datetime.now()
        record.attrs["block_id"] = self.block_id
        return self.soup.add(record)

    def length(self):
        return len([x for x in self.soup.data.values()])

    def search(self, query=None):
        if not query:
            records = self.soup.data.values()

        return records

    def delete(self, id):
        record = self.soup.get(id)
        del self.soup[record]

    def clear(self):
        self.soup.clear()
