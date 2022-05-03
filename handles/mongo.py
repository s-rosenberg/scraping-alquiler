import pymongo

class mongo:
    def __init__(self):
        local_host = pymongo.MongoClient('mongodb://localhost:27017/', connect=False)
        self.db = local_host.alquileres
    
    def get_collection(self, collection):
        return self.db[collection]
    
    def insert_many(self, collection, to_insert):
        query =  collection.insert_many(to_insert)
        return query != None

    