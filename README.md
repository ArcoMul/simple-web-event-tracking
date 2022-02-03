# simple-web-event-tracking

Simple implementation to track browser events in a Postgres SQL database.

✅ Tracks events with freeform properties  
✅ Tracks unique sessions  
✅ Lightweight browser script (<1kb)  
✅ Blocks crawlers using [crawlerdetect](https://github.com/moskrc/crawlerdetect)  
✅ Stores data in Postgres Database, with freeform data in a JSON column  
❌ Fancy graphs and dashboards  
❌ Query interface

Recommended to use with [Redash](https://github.com/getredash/redash) or something alike.

## Setup

Include the following script on your pages:

```html
<script>
  simpleTrack=(function(r,a){var e=[],n=!0;function o(){if(0!==e.length){n=!1;var a=new Image;a.onerror=o,a.src=r+"/image?d="+e.splice(0,1)[0]+"&r="+Math.floor(1e4*Math.random())}else n=!0}return function(r,t){var i={name:r,url:location.pathname+location.search,properties:Object.assign({},a||{},t)};e.push(btoa(JSON.stringify(i))),n&&o()}})(
    "hostname of backend, ex: http://localhost:3000",
    {
      // any default properties to send with any event, ex:
      environment: "production"
    }
  );
</script>
```

Track using, or change the function name to anything else:

```js
simpleTrack('visit', { page: 'product-detail', version: 'b' })
```

## API

`track(name: String, properties: Object)`

Examples:

```js
simpleTrack('visit')
simpleTrack('order button click', { category: 'laptops' })
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
simpleTrack('visit')
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
simpleTrack('visit', { page: 'product-detail' })
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
simpleTrack('visit', { page: 'product-detail' })
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