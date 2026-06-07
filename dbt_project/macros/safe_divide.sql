/*
safe_divide – Divide numerator by denominator, returning null (not an error)
when the denominator is zero or null.

Usage
─────
{{ safe_divide('type1_within_4hr', 'type1_attendances') }}

Parameters
──────────
numerator:   Column name or expression for the dividend.
denominator: Column name or expression for the divisor.
scale:       Optional INTEGER.  When provided, the result is multiplied by
             this factor before being returned.  Useful for expressing the
             result as a percentage (scale=100).

Returns
───────
NUMERIC  – the quotient, or NULL when denominator = 0 or is NULL.
*/

{% macro safe_divide(numerator, denominator, scale=none) %}

    case
        when ({{ denominator }}) = 0 or ({{ denominator }}) is null then null
        else
            {% if scale is not none %}
                ({{ numerator }})::numeric / ({{ denominator }})::numeric * {{ scale }}
            {% else %}
                ({{ numerator }})::numeric / ({{ denominator }})::numeric
            {% endif %}
    end

{% endmacro %}
