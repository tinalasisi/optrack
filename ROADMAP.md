# OpTrack Development Roadmap

This document outlines the planned development path for OpTrack, focusing on improving data storage, scalability, and overall system efficiency.

## Storage Evolution

### Current State (JSON Files)
- Complete database rewrite for each update
- All data loaded into memory during operations
- Limited scalability as database grows
- Simple but inefficient for large datasets

### Phase 1: Append-Only Log (Short-term)
- Implement append-only storage for new grants
- Maintain index files for fast ID lookups
- Separate metadata from content
- Reduced memory footprint
- Elimination of full database rewrites

### Phase 2: Structured Storage (Medium-term)
- Implement SQLite backend option
- Proper database transactions
- Efficient querying capabilities
- Better concurrent access
- Reduced memory requirements
- Still file-based and portable

### Phase 3: Graph Database/API (Long-term)
- Transition to Neo4j for graph relationships
- API-first architecture
- Full separation of data storage and application logic
- Optimized for relationship queries
- Support for advanced filtering and traversal

## Feature Roadmap

### Data Collection Improvements
- [ ] Enhanced rate limiting and retry mechanisms
- [ ] Support for more grant sources
- [ ] More robust error handling
- [ ] Parallel processing of multiple sources

### Analysis & Visualization
- [ ] Basic analytics dashboard
- [ ] Trend visualization 
- [ ] Relationship mapping
- [ ] Export to various formats (beyond CSV)

### System Improvements
- [ ] Comprehensive test suite with CI/CD integration
- [ ] Performance monitoring
- [ ] Automated data validation
- [ ] Configuration through environment variables/config files

## Technical Debt Items

- [ ] Refactor storage logic with proper abstraction layers
- [ ] Improve logging consistency
- [ ] Reduce code duplication in scraper components
- [ ] Create proper package structure

## Immediate Next Steps

1. Implement append-only storage pattern
2. Create index files for fast lookups
3. Update incremental logic to work with new storage format
4. Maintain backward compatibility during transition
5. Update documentation to reflect new storage approach

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-05-12 | Move to append-only storage | Full database rewrites becoming inefficient with growth |
| 2025-05-12 | Plan transition to Neo4j | Graph database structure better fits relationship model of grants |
| 2025-05-12 | Reorganize log structure | More intuitive organization within output directory |