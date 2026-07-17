---
name: new KG submission
about: Describe this issue template's purpose here.
title: 'new KG:'
labels: ''
assignees: ''

---
name: KG Submission

description: Submit a Knowledge Graph to the catalog

title: "KG submission: "

labels:
  - kg-submission

body:

  - type: input
    id: id
    attributes:
      label: KG identifier
      description: Unique identifier
      placeholder: dbnary
    validations:
      required: true


  - type: input
    id: title
    attributes:
      label: KG title
    validations:
      required: true


  - type: input
    id: homepage
    attributes:
      label: Homepage


  - type: input
    id: license
    attributes:
      label: License


  - type: textarea
    id: description
    attributes:
      label: Description
