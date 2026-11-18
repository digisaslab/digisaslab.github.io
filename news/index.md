---
layout: page
title: FGEA CoP News
description: Announcements and records from the Future Generation Enterprise Architecture Community of Practice.
permalink: /news/
wide: true
---

FGEA Community of Practice announcements, event records, and updates.

{% assign published_posts = site.posts | where: "published", true | sort: "date" | reverse %}
## Latest updates

<div class="card-grid">
{% for post in published_posts %}
{% include news-card.html post=post full_summary=true %}
{% endfor %}
</div>
