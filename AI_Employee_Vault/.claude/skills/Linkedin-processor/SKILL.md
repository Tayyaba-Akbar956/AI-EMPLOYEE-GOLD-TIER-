---
name: linkedin-processor
description: Process LinkedIn messages and opportunities. Use when new LinkedIn message or post detected by watcher. Identifies job opportunities, extracts salary and location details, categorizes message types, generates opportunity summaries, and tracks professional networking activity.
---

# LinkedIn Processor Skill

## Purpose
Track professional opportunities, recruiter messages, and important networking activity on LinkedIn to never miss career opportunities or business connections.

## When to Use
- New LinkedIn message from linkedin_watcher.py
- Job opportunity message detected
- Important connection request received
- Professional inquiry or business message
- Post mention or tag detected

## Core Capabilities

### parse_linkedin_content(message_data) -> dict
Extracts structured data from LinkedIn content:
- Sender name and profile URL
- Company name and industry
- Message body text
- Timestamp
- Message type (job/networking/inquiry)
- Returns: Parsed dictionary

### identify_job_opportunity(content) -> bool
Detects job-related messages:
- Keywords: opportunity, position, role, job, opening, hire, recruit, candidate
- Checks for salary mentions
- Looks for job requirements or qualifications
- Identifies application deadlines
- Returns: True if job-related, False otherwise

### extract_salary_info(content) -> dict
Parses compensation details:
- Salary range or specific amount
- Currency (USD, EUR, GBP, etc.)
- Compensation type (annual, hourly, contract)
- Equity or bonus mentions
- Benefits mentions
- Returns: Structured salary data or None

### extract_job_details(content) -> dict
Gets position-specific information:
- Job title and level (junior, senior, lead, etc.)
- Location (city, state, country)
- Work type (remote, hybrid, on-site)
- Required skills and qualifications
- Application deadline
- Returns: Job details dictionary

### generate_opportunity_summary(parsed_data, job_details) -> str
Creates markdown summary:
- Header: "LinkedIn: {Type} from {Sender}"
- Company and position details
- Salary and location prominently displayed
- Key requirements section
- Action items (review, research company, respond)
- Links to sender profile and company page
- Returns: Complete markdown

### categorize_linkedin_content(content) -> str
Determines content type:
- job_opportunity
- networking_request
- business_inquiry
- spam/promotional
- general_message
- Returns: Category string

## Content Filtering

**Process if:**
- Contains job opportunity keywords
- From recruiter or company account
- Connection request from relevant professional
- Business inquiry or partnership message
- Mention/tag in professional context

**Skip if:**
- Generic promotional content
- Irrelevant connection requests
- Automated marketing messages
- General feed updates
- Spam or low-quality content

## Configuration (Company_Handbook.md)

```markdown
## LinkedIn Configuration

### Important Keywords
linkedin_important_keywords:
  - opportunity
  - position
  - role
  - senior developer
  - remote

### Target Companies (prioritize)
linkedin_target_companies:
  - Google
  - Microsoft
  - Amazon
  - Anthropic

### Minimum Salary
linkedin_minimum_salary: 100000  # USD

### Preferred Locations
linkedin_preferred_locations:
  - Remote
  - San Francisco
  - New York
```

## Integration

**Called by:** linkedin_watcher.py (Python watcher with OAuth)

**Calls:**
- vault-management (save opportunity summaries)
- approval-manager (if contract or offer)

**May trigger:** Research workflow (to investigate company)

## Testing Requirements

- Content parsing (all metadata extracted)
- Job opportunity detection (accurate identification)
- Salary extraction (handles various formats)
- Job details extraction (complete information)
- Summary generation (proper formatting)
- Category assignment (correct classification)

---

**Status:** Silver Skill  
**Dependencies:** vault-management  
**Priority:** Medium  
**Test Coverage Required:** >80%