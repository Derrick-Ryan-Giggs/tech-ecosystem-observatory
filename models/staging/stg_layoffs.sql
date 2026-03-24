-- Staging model for layoffs data
-- Source: raw.raw_layoffs_partitioned (partitioned by date monthly, clustered by industry, country)
-- Cleans and standardizes raw layoffs data for downstream transformation

with source as (
    select * from {{ source('raw', 'raw_layoffs_partitioned') }}
),

cleaned as (
    select
        company,
        industry,
        country,
        location,
        stage,
        date,
        total_laid_off,
        percentage_laid_off,
        funds_raised,
        ingested_at
    from source
    where date is not null
      and total_laid_off > 0
)

select * from cleaned