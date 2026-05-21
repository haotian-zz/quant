# TODO

## A Share Data Tables

Current completed foundation:

- Stock list / stock master data
- Trade calendar
- Historical daily prices
- Historical minute prices
- Adjustment factors
- Locally rebuilt adjusted daily prices

### P0: Core Next Tables

1. Daily indicators
   - Status: schema and ETL implemented; full historical fetch still needs to be run.
   - Needed for market cap, float market cap, turnover, volume ratio, PE, PB, dividend yield, and common factor research.

2. Daily limit prices
   - Needed to model A-share limit-up/limit-down constraints, tradability, slippage, and execution realism.

3. Daily suspension/resumption data
   - Needed to filter suspended days and avoid generating impossible trades.

4. Daily share capital / pre-market share data
   - Needed for share capital, float shares, free float, market-cap checks, and capacity constraints.

### P1: Important Data Quality And Universe Tables

5. Historical stock list
   - Needed to build point-in-time universes and reduce survivorship bias.

6. Stock name changes
   - Useful for data cleaning, ST/restructuring/renaming investigation, and historical debugging.

7. ST stock list
   - Needed for strategy filters and risk controls around ST and delisting-risk stocks.

8. ST risk warning board stocks
   - Related to ST filtering; useful for fuller A-share risk-state coverage.

9. Listed company basic information
   - Useful metadata layer for company attributes, region, industry, and research context.

### P2: Strategy-Dependent Tables

10. Weekly and monthly prices
    - Can be generated locally from daily data; fetch only if provider fields or update workflow are clearly useful.

11. Weekly/monthly adjusted prices
    - Prefer generating locally from daily prices and adjustment factors for consistent adjustment logic.

12. Provider adjusted prices
    - Lower priority because local `none + adj_factor -> qfq/hfq` already exists; useful mainly for cross-checking.

13. Shanghai/Shenzhen-Hong Kong Stock Connect stock list
    - Useful if strategies need northbound eligibility or stock-connect universe filters.

14. Stock Connect top traded stocks
    - Useful for flow and event factors, but not core warehouse infrastructure.

15. Southbound Stock Connect top traded stocks and turnover stats
    - Lower priority while the warehouse remains A-share focused.

### P3: Defer

16. Realtime daily and realtime minute data
    - Requires online scheduling, overwrite rules, intraday state handling, and recovery logic. Defer until live monitoring or trading is in scope.

17. Generic quote interface
    - Too broad for formal table design. Prefer domain-specific warehouse tables.

18. Company management, compensation, and shareholding
    - Useful for fundamental/event research, but not the next core market-data layer.

19. BSE old/new code mapping
    - Small and useful; can be added opportunistically, but it is not a major dependency.

20. IPO new listings
    - Useful for IPO/listing-age filters, but lower priority than daily indicators, limit prices, suspensions, and point-in-time universe data.
