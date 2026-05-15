alter table public.equity_universe
  add column if not exists beta numeric,
  add column if not exists revenue_fy2021 numeric,
  add column if not exists revenue_fy2022 numeric,
  add column if not exists ebitda_fy2021 numeric,
  add column if not exists ebitda_fy2022 numeric,
  add column if not exists pat_fy2021 numeric,
  add column if not exists pat_fy2022 numeric,
  add column if not exists eps_fy2021 numeric,
  add column if not exists eps_fy2022 numeric,
  add column if not exists eps_fy23 numeric,
  add column if not exists eps_fy24 numeric,
  add column if not exists eps_fy25 numeric;
