---
name: caching-strategy
description: Implement caching strategies using Redis, Memcached, or CDN for performance optimization. Covers cache invalidation, TTL management, and cache warming.
---

# Caching Strategy Skill

## Purpose
Implement robust caching strategies to improve application performance and reduce database load.

## When to Use
- API response caching
- Database query result caching
- Session storage
- Rate limiting implementation
- Expensive computation caching
- Static asset caching (CDN)

## What It Does

### 1. Cache Layer Design
- **Application-level**: Redis, Memcached
- **Database-level**: Query result caching
- **CDN-level**: Static assets, images
- **Browser-level**: HTTP caching headers

### 2. Cache Strategies

#### Cache-Aside (Lazy Loading)
```python
def get_user(user_id):
    # Check cache first
    user = cache.get(f"user:{user_id}")
    if user:
        return user

    # Cache miss - fetch from DB
    user = db.query(User).filter(User.id == user_id).first()

    # Store in cache with TTL
    cache.set(f"user:{user_id}", user, ttl=3600)
    return user
```

#### Write-Through
```python
def update_user(user_id, data):
    # Update database
    db.query(User).filter(User.id == user_id).update(data)
    db.commit()

    # Update cache immediately
    cache.set(f"user:{user_id}", updated_user, ttl=3600)
```

#### Write-Behind (Write-Back)
```python
def update_user_async(user_id, data):
    # Update cache immediately
    cache.set(f"user:{user_id}", data, ttl=3600)

    # Queue database update (async)
    task_queue.enqueue(write_to_db, user_id, data)
```

### 3. Cache Invalidation

#### Time-Based (TTL)
```python
cache.set("key", value, ttl=3600)  # Expires in 1 hour
```

#### Event-Based
```python
def on_user_update(user_id):
    cache.delete(f"user:{user_id}")
    cache.delete(f"user_list")  # Invalidate list cache
```

#### Pattern-Based
```python
# Delete all keys matching pattern
cache.delete_pattern("user:*")
```

## Implementation Guide

### Step 1: Setup Redis
```python
# FastAPI example
from redis import Redis

redis_client = Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)
```

### Step 2: Caching Decorator
```python
from functools import wraps
import json

def cache_result(ttl=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"

            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )
            return result
        return wrapper
    return decorator

# Usage
@cache_result(ttl=3600)
async def get_tasks(user_id: str):
    return await db.query(Task).filter(Task.user_id == user_id).all()
```

### Step 3: Cache Warming
```python
async def warm_cache():
    """Pre-populate cache with frequently accessed data"""
    popular_users = await db.query(User).limit(100).all()
    for user in popular_users:
        cache.set(f"user:{user.id}", user, ttl=7200)
```

## Best Practices

### Cache Key Design
```
✅ Good: user:123, task:456:details
❌ Bad: u123, t456d
```

### TTL Strategy
- **Static data**: 24 hours+
- **User data**: 1-6 hours
- **Real-time data**: 1-5 minutes
- **Computed results**: Based on computation cost

### Cache Size Management
```python
# Set max memory policy
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## Performance Metrics

**Before Caching:**
- API response time: 500ms
- Database load: 1000 queries/sec

**After Caching:**
- API response time: 50ms (10x faster)
- Database load: 100 queries/sec (90% reduction)
- Cache hit rate: 85%+

## Use Cases

1. **API Response Caching**: Cache GET endpoints
2. **Session Storage**: User sessions in Redis
3. **Rate Limiting**: Track API calls per user
4. **Leaderboards**: Sorted sets in Redis
5. **Real-time Analytics**: Aggregate counts

## Constitution Compliance
- ✅ Performance optimization
- ✅ Reduces database load
- ✅ Scalable architecture
- ✅ User data isolation maintained

---

**Status:** Active
**Priority:** 🔴 Critical (Performance essential)
**Version:** 1.0.0
**Category:** Performance Optimization
