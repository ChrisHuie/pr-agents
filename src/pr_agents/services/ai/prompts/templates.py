"""Persona-based prompt templates for code summarization."""

EXECUTIVE_TEMPLATE = """You are summarizing code changes for an executive audience.
Repository: {repo_name} ({repo_type})

PR Title: {pr_title}
Files Changed: {file_count}
Lines Added: {additions}
Lines Deleted: {deletions}

Repository Context:
{repo_context}

Provide a 1-2 sentence executive summary focusing on:
- Business functionality added/modified
- Scope and impact
- Key integrations or features

Guidelines:
- Be concise and high-level
- Focus on business value
- Avoid technical implementation details
- Mention the main component/feature affected

Example: "Sevio Bid Adapter added to Prebid.js and supports banner and native media types"

Code Changes Summary:
{changes_summary}

Executive Summary:"""

PRODUCT_TEMPLATE = """You are summarizing code changes for a product manager.
Repository: {repo_name} ({repo_type})

PR Title: {pr_title}
PR Description Preview: {pr_description_preview}

Changes Overview:
- Files Changed: {file_count}
- Lines Added: {additions}
- Lines Deleted: {deletions}
- File Types: {file_types}

Repository Context:
{repo_context}

Provide a product-focused summary (2-4 sentences) that includes:
- Specific features or capabilities added/modified
- Supported configurations or options
- Key functions or APIs implemented
- User-facing impacts or behavior changes
- Integration points with other systems

Guidelines:
- Be more detailed than executive summary
- Focus on feature capabilities
- Mention specific functionality names
- Include configuration options if relevant

Example: "Sevio Bid Adapter added to Prebid.js with comprehensive support for banner (300x250, 728x90) and native ad formats. Features include Ethereum and Solana digital wallet detection for Web3 targeting, GDPR/CCPA compliance handling, and real-time bid adjustment based on user engagement metrics. Implements standard adapter callbacks (onBidWon, onBidderError, onTimeout) plus custom user sync with configurable pixel and iframe endpoints supporting up to 5 concurrent syncs."

Detailed Code Changes:
{detailed_changes}

Product Summary:"""

DEVELOPER_TEMPLATE = """You are summarizing code changes for a software engineer.
Repository: {repo_name} ({repo_type})

PR Title: {pr_title}
Base Branch: {base_branch}
Head Branch: {head_branch}

Technical Overview:
- Files Changed: {file_count}
- Lines Added: {additions}
- Lines Deleted: {deletions}
- Primary Language: {primary_language}
- Modified Paths: {modified_paths}

Repository Structure and Context:
{repo_context}

Code Patterns Detected:
{code_patterns}

Provide a detailed technical summary (4-6 sentences) that includes:
- New classes, modules, or libraries introduced with their purpose
- Technical implementation details and design patterns used
- Specific algorithms or data structures implemented
- API changes, method signatures, and interface modifications
- Dependencies added or modified (with versions if available)
- Test coverage changes and testing approach
- Performance implications or optimizations
- Security considerations or cryptographic implementations
- Database schema changes or data model updates
- Breaking changes, deprecations, or migration requirements
- Error handling and edge cases addressed
- Configuration changes and their impacts

Guidelines:
- Be technically precise and comprehensive
- Use exact class/function/variable names from the code
- Describe implementation approach and rationale
- Note architectural patterns (MVC, Observer, Factory, etc.)
- Mention specific technologies and libraries used
- Include performance complexity if relevant (O(n), O(log n), etc.)
- Highlight any potential technical debt or TODOs

Example: "Sevio Bid Adapter (modules/sevioBidAdapter.js) and CryptoUtils library (libraries/cryptoUtils/index.js) added to Prebid.js. The CryptoUtils library implements SHA-256 hashing and AES-GCM encryption using the Web Crypto API for secure bid request signing, with fallback to CryptoJS for older browsers. The Sevio adapter extends the Prebid BaseAdapter class, implementing interpretResponse() with custom bid parsing logic that handles nested JSON responses, buildRequests() with dynamic endpoint selection based on datacenter location, and isBidRequestValid() with strict schema validation using Joi. Adds three new dependencies: crypto-js@4.1.1 for legacy support, joi@17.9.0 for validation, and ethers@6.7.0 for Web3 wallet detection. Test coverage includes 47 unit tests (93% line coverage) using Sinon for mocking external API calls and Chai for assertions. Performance optimization through request batching reduces API calls by 60% for multi-slot pages. Implements OWASP-compliant input sanitization and rate limiting (100 req/min) to prevent abuse."

Full Code Diff Analysis:
{full_diff_analysis}

Technical Summary:"""

# Specialized templates for specific repository types
PREBID_ADAPTER_TEMPLATE = """You are analyzing a new Prebid adapter implementation.
Adapter Name: {adapter_name}
Repository: {repo_name}

Changes Overview:
{changes_summary}

For this Prebid adapter, identify:
1. Supported media types (banner, video, native)
2. Required and optional bid parameters
3. Special features (user syncing, timeout handling, etc.)
4. Compliance with Prebid standards

Provide a {persona}-level summary appropriate for your audience.

Summary:"""
