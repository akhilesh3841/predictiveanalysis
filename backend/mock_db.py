"""
Mock MongoDB implementation for testing without real MongoDB connection
"""
import logging
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

class MockCursor(list):
    """A lightweight cursor supporting .sort() and .limit() chaining"""
    def __init__(self, data):
        super().__init__(data)
        self._projection = None
        self._sort_key = None
        self._sort_dir = 1

    def sort(self, key, direction=1):
        if isinstance(key, list):
            for k, d in reversed(key):
                list.sort(self, key=lambda x: x.get(k), reverse=(d == -1))
        else:
            list.sort(self, key=lambda x: x.get(key), reverse=(direction == -1))
        self._sort_key = key
        self._sort_dir = direction
        return self

    def limit(self, n):
        self[:] = self[:n]
        return self

    def skip(self, n):
        self[:] = self[n:]
        return self

    def __iter__(self):
        return list.__iter__(self)

    def count_documents(self, query=None):
        return len(self)


class MockCollection:
    """Mock MongoDB collection"""
    def __init__(self, name):
        self.name = name
        self.data = []
    
    def insert_many(self, documents):
        """Insert multiple documents"""
        for doc in documents:
            if '_id' not in doc:
                doc['_id'] = len(self.data)
            self.data.append(doc)
        return [doc['_id'] for doc in documents]
    
    def find(self, query=None, projection=None, *args, **kwargs):
        """Find documents, supporting query + projection (pymongo-like)"""
        if query is None:
            query = {}
        results = [doc for doc in self.data if self._match_query(doc, query)]
        if projection:
            exclude = all(
                v == 0
                for v in projection.values()
            )
            rebuilt = []
            for doc in results:
                if exclude:
                    rebuilt.append(
                        {k: v for k, v in doc.items() if projection.get(k, 1) != 0}
                    )
                else:
                    rebuilt.append(
                        {k: v for k, include in projection.items() if include and k in doc for v in [doc[k]]}
                    )
            return MockCursor(rebuilt)
        return MockCursor(results)

    def _match_query(self, doc, query):
        """Check if document matches query"""
        for key, value in query.items():
            if isinstance(value, dict) and set(value.keys()).intersection(
                {"$gt", "$lt", "$gte", "$lte", "$ne", "$exists", "$in"}
            ):
                if "$exists" in value:
                    present = key in doc and doc[key] is not None
                    if bool(value["$exists"]) != present:
                        return False
                if key in doc:
                    dv = doc[key]
                    if "$gt" in value and not (dv > value["$gt"]):
                        return False
                    if "$lt" in value and not (dv < value["$lt"]):
                        return False
                    if "$gte" in value and not (dv >= value["$gte"]):
                        return False
                    if "$lte" in value and not (dv <= value["$lte"]):
                        return False
                    if "$ne" in value and dv == value["$ne"]:
                        return False
                    if "$in" in value and dv not in value["$in"]:
                        return False
                else:
                    continue
            else:
                if key not in doc:
                    return False
                if isinstance(value, dict):
                    for op, vval in value.items():
                        if op == "$gt" and not (doc[key] > vval):
                            return False
                        if op == "$lt" and not (doc[key] < vval):
                            return False
                        if op == "$ne" and doc[key] == vval:
                            return False
                elif doc[key] != value:
                    return False
        return True
    
    def find_one(self, query=None):
        """Find single document"""
        results = self.find(query)
        return results[0] if results else None
    
    def count_documents(self, query=None):
        """Count documents matching query"""
        if query is None or query == {}:
            return len(self.data)
        return len(self.find(query))
    
    def delete_many(self, query):
        """Delete documents"""
        initial_count = len(self.data)
        self.data = [doc for doc in self.data if not self._match_query(doc, query)]
        return type('obj', (object,), {'deleted_count': initial_count - len(self.data)})()
    
    def create_index(self, keys):
        """Mock index creation"""
        pass
    
    def aggregate(self, pipeline):
        """Mock aggregation"""
        results = self.data.copy()
        for stage in pipeline:
            if '$group' in stage:
                results = self._apply_group(results, stage['$group'])
            elif '$sort' in stage:
                results = self._apply_sort(results, stage['$sort'])
            elif '$limit' in stage:
                results = results[:stage['$limit']]
            elif '$match' in stage:
                results = [doc for doc in results if self._match_query(doc, stage['$match'])]
        return results
    
    def _match_query(self, doc, query):
        """Check if document matches query"""
        for key, value in query.items():
            if key not in doc:
                return False
            if isinstance(value, dict):
                if '$gt' in value and not (doc[key] > value['$gt']):
                    return False
                if '$lt' in value and not (doc[key] < value['$lt']):
                    return False
            elif doc[key] != value:
                return False
        return True
    
    def _apply_group(self, docs, group_spec):
        """Apply $group aggregation"""
        grouped = {}
        for doc in docs:
            # Handle _id field - check if it's a field reference ($field) or constant
            id_spec = group_spec['_id']
            if isinstance(id_spec, str) and id_spec.startswith('$'):
                # Field reference like "$ProductID"
                group_key = doc.get(id_spec[1:])
            else:
                # Constant value or None
                group_key = id_spec
                
            if group_key not in grouped:
                grouped[group_key] = {'_id': group_key}
                # Initialize all aggregation fields
                for key, value in group_spec.items():
                    if key != '_id' and isinstance(value, dict):
                        if '$sum' in value:
                            grouped[group_key][key] = 0
                        elif '$avg' in value:
                            grouped[group_key][key] = 0
                        elif '$first' in value:
                            grouped[group_key][key] = None
                        elif '$last' in value:
                            grouped[group_key][key] = None
            
            for key, value in group_spec.items():
                if key == '_id':
                    continue
                if isinstance(value, dict):
                    if '$sum' in value:
                        field_name = value['$sum']
                        if isinstance(field_name, int):
                            # Constant sum like $sum: 1 for counting
                            grouped[group_key][key] += field_name
                        elif isinstance(field_name, str) and field_name.startswith('$'):
                            # Field reference like "$Revenue"
                            field_name = field_name[1:]
                            grouped[group_key][key] += doc.get(field_name, 0)
                        else:
                            grouped[group_key][key] += field_name
                    elif '$avg' in value:
                        field_name = value['$avg']
                        if isinstance(field_name, str) and field_name.startswith('$'):
                            field_name = field_name[1:]
                        if key not in grouped[group_key]:
                            grouped[group_key][key] = []
                        grouped[group_key][key].append(doc.get(field_name, 0))
                    elif '$first' in value:
                        # Take first value for this group
                        if grouped[group_key][key] is None:
                            field_name = value['$first']
                            if isinstance(field_name, str) and field_name.startswith('$'):
                                field_name = field_name[1:]
                            grouped[group_key][key] = doc.get(field_name)
                    elif '$last' in value:
                        # Always update with the latest value (this is last when iterating)
                        field_name = value['$last']
                        if isinstance(field_name, str) and field_name.startswith('$'):
                            field_name = field_name[1:]
                        grouped[group_key][key] = doc.get(field_name)
        
        # Convert avg lists to actual averages
        for doc in grouped.values():
            for key, value in list(doc.items()):
                if isinstance(value, list):
                    doc[key] = sum(value) / len(value) if value else 0
        
        return list(grouped.values())
    
    def _apply_sort(self, docs, sort_spec):
        """Apply $sort"""
        for key, direction in reversed(sort_spec.items()):
            docs.sort(key=lambda x: x.get(key, 0), reverse=(direction == -1))
        return docs


class MockDatabase:
    """Mock MongoDB database"""
    def __init__(self, name):
        self.name = name
        self.collections = {}
    
    def __getitem__(self, collection_name):
        """Get or create collection"""
        if collection_name not in self.collections:
            self.collections[collection_name] = MockCollection(collection_name)
        return self.collections[collection_name]
    
    def get_collection(self, collection_name):
        """Get collection"""
        return self[collection_name]
    
    def command(self, cmd, **kwargs):
        """Mock database command"""
        if cmd == 'ping':
            return {'ok': 1}
        return {'ok': 1}


class MockMongoClient:
    """Mock MongoDB client"""
    def __init__(self, uri=None, **kwargs):
        self.uri = uri
        self.databases = {}
        # Simulate connection latency
        import time
        time.sleep(0.1)
    
    def __getitem__(self, database_name):
        """Get or create database"""
        if database_name not in self.databases:
            self.databases[database_name] = MockDatabase(database_name)
        return self.databases[database_name]
    
    def close(self):
        """Close connection"""
        pass
    
    @property
    def admin(self):
        """Admin database for ping"""
        return MockAdminDb()


class MockAdminDb:
    """Mock admin database"""
    def command(self, cmd):
        """Mock ping command"""
        if cmd == 'ping':
            return {'ok': 1}


def generate_mock_data():
    """Generate mock data for testing"""
    # Generate transactions
    transactions = []
    products = {
        'Product A': 'Laptop Computer',
        'Product B': 'Wireless Mouse',
        'Product C': 'USB-C Cable',
        'Product D': 'Monitor 27"',
        'Product E': 'Mechanical Keyboard'
    }
    customers = ['Customer 1', 'Customer 2', 'Customer 3']
    countries = ['USA', 'UK', 'Germany', 'France', 'Japan']
    
    base_date = datetime.now() - timedelta(days=90)
    for i in range(100):
        product_id = random.choice(list(products.keys()))
        transactions.append({
            '_id': i,
            'TransactionID': f'TXN{i:05d}',
            'Date': base_date + timedelta(days=i % 30),
            'ProductID': product_id,
            'ProductName': products[product_id],
            'CustomerID': random.choice(customers),
            'Quantity': random.randint(1, 10),
            'UnitPrice': round(random.uniform(10, 500), 2),
            'Revenue': round(random.randint(1, 10) * random.uniform(10, 500), 2),
            'Country': random.choice(countries)
        })
    
    return transactions


# Monkey-patch for using mock with actual MongoDB code
def create_mock_client():
    """Create a mock MongoDB client"""
    return MockMongoClient()
