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
SELECT properties->>'page' as page, COUNT(*) as count
FROM events
GROUP BY properties->>'page'
ORDER BY count DESC
```

### Tracking page conversion

Add a track event to every page load, include a page name. Find
out later events using a join

```js
track('page', { page: 'product-detail' })
```

```sql
SELECT
  'conversion' as label,
  COUNT(DISTINCT product_page.session_id) as product_detail_count,
  COUNT(DISTINCT checkout_page.session_id) as checkout_count,
  COUNT(DISTINCT checkout_page.session_id)::decimal / COUNT(DISTINCT product_page.session_id)::decimal as conversion
FROM sessions
LEFT JOIN events as product_page
  ON product_page.session_id = sessions.id
  AND product_page.properties->>'page' = 'product-detail'
LEFT JOIN events as checkout_page
  ON checkout_page.session_id = sessions.id
  AND checkout_page.properties->>'page' = 'checkout'
  AND checkout_page.created > product_page.created
GROUP BY label
```