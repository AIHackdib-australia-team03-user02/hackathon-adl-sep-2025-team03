---
title: "Sensitivity labels"
linkTitle: "Sensitivity labels"
weight: 10
description: "This section describes the configuration of sensitivity labels within Microsoft Purview associated with systems built according to guidance in ASD's Blueprint for Secure Cloud."
---

{{% alert title="Instruction" color="dark" %}}

The below pages outline the *as built* configuration for ASD's *Blueprint for Secure Cloud* (the Blueprint) for the Microsoft Purview portal at the following URL:

<https://purview.microsoft.com/informationprotection/informationprotectionlabels/sensitivitylabels>

The settings described on these pages provide a baseline implementation for a system configured using the Blueprint. Any implementation implied by these pages should not be considered as prescriptive as to how an organisation must scope, build, document, or assess a system.

Implementation of the guidance provided by the Blueprint will differ depending on an organisation’s operating context and organisational culture. Organisations should implement the Blueprint in alignment with their existing change management, business processes and frameworks.

Placeholders such as `<ORGANISATION.GOV.AU>`, `<BLUEPRINT.GOV.AU>` and `<TENANT-NAME>` should be replaced with the relevant details as required.

{{% /alert %}}

{{% alert title="Migrating labelling schemes" color="info" %}}

The NATIONAL CABINET special handling marking has been formally retired.

Organisations with existing labelling schemes may find the [migrating labelling schemes]({{<ref "tools/purview/migrating-labelling-schemes">}}) guidance useful when modifying sensitivity labels.

{{% /alert %}}

{{% alert title="Parent label deprecation" color="warning" %}}

Microsoft is deprecating parent sensitivity labels in favour of label groups.

During the migration process, sublabels may be automatically generated for each existing parent label. These newly created sublabels may be included in publishing policies, making them visible and selectable by end users.

Organisations are encouraged to conduct a review of label configurations prior to migration, and to validate the post-migration labelling scheme and associated policy behaviours.

For guidance on preparing for and mitigating potential impacts, please refer to [Microsoft's label migration documentation](https://learn.microsoft.com/en-au/purview/migrate-sensitivity-label-scheme).

{{% /alert %}}
