# simple-web-event-tracking

Simple implementation to track browser events in a Postgres SQL database.

✅ Tracks events with freeform properties  
✅ Tracks unique sessions  
✅ Lightweight browser script (<1kb)  
✅ Blocks crawlers using [crawlerdetect](https://github.com/moskrc/crawlerdetect)  
✅ Stores data in Postgres Database, with freeform data in a JSON column  

## Setup

Include the following script on your pages:

```html
<script>
  function track(n, p) {
    var d={name:n,url:location.pathname+location.search,properties:p};
    var e=btoa(JSON.stringify(d));
    var i=new Image();
    i.src="<url of event tracking hosting>/image?d="+e;
  }
</script>
```

Track using, or change the function name to anything else:

```js
track('visit', { page: 'product-detail', version: 'b' })
```

## API

`track(name: String, properties: Object)`

Examples:

```js
track('visit')
track('order button click', { category: 'laptops' })
```

## Data structure

```
Session
-------
id: uuid
started: timestamp
```

```
Event
-----
id: serial
session_id: uuid
created: timestamp
name: string
url: string?
properties: JSON?
```

## Use-cases

### Track most visited urls

Add a simple track event to every page load, possibly add a page name
to every event to group the same type of pages

```js
track('visit')
```

```sql
SELECT url, COUNT(*) as count
FROM events
WHERE name = 'visit'
GROUP BY url
ORDER BY count DESC
```

### Track most visited pages

Add a track event to every page load, add a page name
to every event to group the same type of pages

```js
track('visit', { page: 'product-detail' })
```

```sql
SELECT properties->>'page' as page, COUNT(*) as count
FROM events
WHERE name = 'visit'
GROUP BY properties->>'page'
ORDER BY count DESC
```

### Tracking page conversion

Add a track event to every page load, include a page name. Find
out later events using a join

```js
track('visit', { page: 'product-detail' })
```

```sql
SELECT
  unnest(array['index', 'product', 'checkout']) as step,
  unnest(array[
      COUNT(DISTINCT index.session_id),
      COUNT(DISTINCT product.session_id),
      COUNT(DISTINCT checkout.session_id)
  ]) as value
FROM events AS index
LEFT JOIN events AS product
  ON product.session_id = index.session_id 
  AND product.properties->>'page' = 'product-detail'
  AND product.created > index.created
LEFT JOIN events AS checkout
  ON checkout.session_id = index.session_id 
  AND checkout.properties->>'page' = 'checkout'
  AND checkout.created > product.created
WHERE index.name = 'visit' AND index.properties->>'page' = 'index'
```

### Tracking bounce rate

Using the same tracking settings as the page conversion example

```sql
SELECT 
    properties->>'page' as page,
    COUNT(id) AS total,
    COUNT(DISTINCT events.session_id) AS unique,
    COUNT(sessions.session_id) AS bounces
FROM events
LEFT JOIN (
    /* Get sessions and the number of pages visited */
    SELECT session_id, COUNT(id) as count
    FROM events
    GROUP BY session_id
) as sessions ON sessions.session_id = events.session_id AND sessions.count = 1
WHERE name = 'visit'
GROUP BY properties->>'page'
ORDER BY total DESC
```