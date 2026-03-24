-- Mart: tech ecosystem health by industry
-- Joins layoffs with YC company counts to correlate
-- startup activity with layoff trends per sector

with layoffs as (
    select
        industry,
        sum(total_laid_off)          as total_laid_off,
        count(*)                     as num_layoff_events,
        round(sum(funds_raised), 2)  as total_funds_raised
    from {{ ref('stg_layoffs') }}
    group by industry
),

yc as (
    select
        industry,
        count(*)                                              as total_yc_companies,
        countif(status = 'Active')                            as active_companies,
        countif(status = 'Acquired')                          as acquired_companies,
        round(avg(cast(team_size as float64)), 0)             as avg_team_size
    from {{ ref('stg_yc_companies') }}
    where industry is not null
    group by industry
),

joined as (
    select
        coalesce(l.industry, y.industry)  as industry,
        l.total_laid_off,
        l.num_layoff_events,
        l.total_funds_raised,
        y.total_yc_companies,
        y.active_companies,
        y.acquired_companies,
        y.avg_team_size,
        round(
            safe_divide(l.total_laid_off, y.total_yc_companies), 2
        )                                 as layoffs_per_yc_company
    from layoffs l
    full outer join yc y
        on lower(trim(l.industry)) = lower(trim(y.industry))
)

select * from joined
order by total_laid_off desc