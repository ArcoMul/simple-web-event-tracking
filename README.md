# simple-web-event-tracking

Simple implementation to start tracking browser events in an SQL database.

## Setup

Including the following script on your page:

```html
<script>
  function track(n, p) {
    var d={name:n,url:location.pathname+location.search,properties:p};
    var e=btoa(JSON.stringify(d));
    var i=new Image();
    i.src="http://localhost:3000/image?d="+e;
  }
</script>
```

## API

`track(name: String, properties: Object)`

Examples:

```js
track('page')
track('order button click', { category: 'laptops' })
```

## Data structure

```
Session
-------
id
started
```

```
Event
-----
id
session_id
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
track('page')
```

```sql
SELECT url, COUNT(*) as count FROM events GROUP BY url ORDER BY count DESC
```

### Track most visited pages

Add a track event to every page load, add a page name
to every event to group the same type of pages

```js
track('page', { page: 'product-detail' })
```

```sql
SELECT url, COUNT(*) as count FROM events GROUP BY properties->page ORDER BY count DESC
```

```sql
SELECT JSON_UNQUOTE(JSON_EXTRACT(properties, "$.page")) as page, COUNT(*) as count FROM events GROUP BY JSON_EXTRACT(properties, "$.page") ORDER BY count DESC
```

### Tracking page conversion

Add a track event to every page load, include a page name. Find
out later events using a join

```js
track('page', { page: 'product-detail' })
```

```sql
SELECT
    properties->page as page,
    COUNT(id) as product_detail_count,
    COUNT(after.id) as checkout_count,
    COUNT(after.id) / COUNT(id) as conversion
FROM events
WHERE properties->page IS 'product-detail'
LEFT JOIN events as after
ON after.session_id = events.session_id
    AND after.created > events.created
    AND properties->page IS 'checkout'
GROUP BY properties->page
```

```sql
SELECT
    JSON_UNQUOTE(JSON_EXTRACT(properties, "$.page")) as page,
    COUNT(id) as product_detail_count,
    COUNT(after.id) as checkout_count,
    COUNT(after.id) / COUNT(id) as conversion
FROM events
WHERE JSON_UNQUOTE(JSON_EXTRACT(properties, "$.page")) IS 'product-detail'
LEFT JOIN events as after
ON after.session_id = events.session_id
    AND after.created > events.created
    AND JSON_UNQUOTE(JSON_EXTRACT(properties, "$.page")) IS 'checkout'
GROUP BY JSON_EXTRACT(properties, "$.page")
```