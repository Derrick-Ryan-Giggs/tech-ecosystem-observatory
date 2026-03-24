-- Staging model for YC companies data
-- Source: raw.raw_yc_companies_partitioned
-- Partitioned by ingested_at, clustered by industry, status
-- Cleans nulls and standardizes fields

with source as (
    select * from {{ source('raw', 'raw_yc_companies_partitioned') }}
),

cleaned as (
    select
        id,
        name,
        slug,
        batch,
        status,
        industry,
        all_locations,
        website,
        team_size,
        tags,
        ingested_at
    from source
    where name is not null
)

select * from cleaned