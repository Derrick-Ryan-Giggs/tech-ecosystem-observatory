-- Mart: monthly layoffs trends
-- Aggregates layoffs by month, industry and country
-- Used for time-series analysis in the dashboard

with layoffs as (
    select * from {{ ref('stg_layoffs') }}
),

monthly as (
    select
        date_trunc(date, month)                          as month,
        industry,
        country,
        count(*)                                         as num_events,
        sum(total_laid_off)                              as total_laid_off,
        round(avg(percentage_laid_off), 2)               as avg_percentage_laid_off,
        round(sum(funds_raised), 2)                      as total_funds_raised
    from layoffs
    group by 1, 2, 3
)

select * from monthly
order by month desc