# AbstractReader

`AbstractReader` is the base class every instrument reader subclasses. It owns
the pipeline — file discovery, native-grid detection, caching, the L3
presentation steps, reporting and `df.attrs` stamping — and leaves three hooks
to the subclass: `_raw_reader`, `_QC` and (optionally) `_process`.

- What each stage may add or destroy, and what is cached:
  [Data Levels (L0–L3)](../guide/data-levels.md).
- The QC machinery and status decoding the hooks plug into:
  [RawDataReader Reference](../guide/reader-reference.md).
- Writing a new subclass, step by step, with the registry entry, the tests and
  the docs page it needs: [Contributing a reader](../guide/contributing-reader.md).

You do not instantiate it directly — the
[`RawDataReader`](RawDataReader/index.md) factory picks the subclass from the
instrument name.

## API

::: AeroViz.rawDataReader.core.AbstractReader
    options:
        show_source: false
        show_bases: true
        show_inheritance_diagram: false
        members_order: alphabetical
        show_if_no_docstring: false
        filters:
            - "!^_"
            - "!^__init__"
        docstring_section_style: table
        heading_level: 3
        show_signature_annotations: true
        separate_signature: true
        group_by_category: true
        show_category_heading: true
