/*
generate_schema_name – Override dbt's default schema naming behaviour.

By default dbt generates schema names as `<target_schema>_<custom_schema>`,
which would produce `staging_staging` or `staging_marts`.  This macro makes
dbt use the custom schema name directly so models land in the correct
PostgreSQL schemas: staging and marts.

This is the standard community pattern for multi-schema dbt projects.
*/

{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}

    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}

{%- endmacro %}
