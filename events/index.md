---
layout: page
title: FGEA CoP Events
description: Upcoming symposiums and historical event records from the Future Generation Enterprise Architecture Community of Practice.
permalink: /events/
wide: true
---

{{ site.data.organization.symposiums.description }}

## Upcoming events

{% if site.upcoming_events.size > 0 %}
<div class="card-grid">
{% for event in site.upcoming_events %}
{% include event-card.html event=event full_summary=true %}
{% endfor %}
</div>
{% else %}
No upcoming events have been published. [Contact FGEA CoP]({{ '/contact/' | relative_url }}) to express interest in future symposiums.
{% endif %}

## Historical event records

{% if site.past_events.size > 0 %}
<div class="card-grid">
{% for event in site.past_events %}
{% include event-card.html event=event full_summary=true %}
{% endfor %}
</div>
{% else %}
No historical event records have been published.
{% endif %}
