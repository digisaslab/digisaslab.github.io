---
layout: page
title: About FGEA CoP
description: The purpose, principles, and leadership of the Future Generation Enterprise Architecture Community of Practice.
permalink: /about/
wide: true
---

## {{ site.data.organization.purpose.heading }}

{{ site.data.organization.purpose.lead }}

{{ site.data.organization.purpose.detail }}

## Our principles

{% for principle in site.data.organization.principles %}
### {{ principle.name }}

{{ principle.description }}
{% endfor %}

## Leadership

<div class="card-grid">
{% for person in site.data.people.leadership %}
{% include person-card.html person=person %}
{% endfor %}
</div>

## Advisory panel

<div class="card-grid">
{% for person in site.data.people.advisory_panel %}
{% include person-card.html person=person %}
{% endfor %}
</div>

## Advisory committee chairs

<div class="card-grid">
{% for person in site.data.people.advisory_committee_chairs %}
{% include person-card.html person=person %}
{% endfor %}
</div>

The community purpose and structure are preserved from the
[DigiSAS Lab FGEA CoP overview](https://www.digisaslab.org/fgea-cop/).
