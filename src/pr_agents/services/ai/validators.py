"""Validators for AI-generated summaries."""

import re
from typing import List, Tuple

from loguru import logger


class SummaryValidator:
    """Validates AI-generated summaries for quality and accuracy."""
    
    def __init__(self):
        """Initialize validator with quality rules."""
        self.min_words = {
            "executive": 5,
            "product": 10,
            "developer": 20,
        }
        
        self.max_words = {
            "executive": 50,
            "product": 100,
            "developer": 200,
        }
        
        # Common quality issues to check
        self.quality_patterns = {
            "placeholder": re.compile(r'\[.*?\]|\{.*?\}|<.*?>|TODO|FIXME|XXX'),
            "repetition": re.compile(r'\b(\w+)\s+\1\b', re.IGNORECASE),
            "incomplete": re.compile(r'\.\.\.$|etc\.$|and so on\.$'),
            "generic": re.compile(r'^(This PR|This commit|These changes|The code)', re.IGNORECASE),
        }
    
    def validate_summary(
        self, 
        summary: str, 
        persona: str,
        code_context: dict = None
    ) -> Tuple[bool, List[str]]:
        """Validate a summary for quality and appropriateness.
        
        Args:
            summary: The generated summary
            persona: The persona type
            code_context: Optional code context for validation
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check length requirements
        word_count = len(summary.split())
        min_words = self.min_words.get(persona, 5)
        max_words = self.max_words.get(persona, 200)
        
        if word_count < min_words:
            issues.append(f"Summary too short: {word_count} words (minimum: {min_words})")
        elif word_count > max_words:
            issues.append(f"Summary too long: {word_count} words (maximum: {max_words})")
        
        # Check for quality issues
        for issue_name, pattern in self.quality_patterns.items():
            if pattern.search(summary):
                issues.append(f"Contains {issue_name} content")
        
        # Check for required content based on persona
        if persona == "executive":
            if not self._has_business_language(summary):
                issues.append("Missing business-oriented language")
        elif persona == "developer":
            if not self._has_technical_terms(summary):
                issues.append("Missing technical details")
        
        # Validate against code context if provided
        if code_context:
            validation_issues = self._validate_against_context(summary, code_context, persona)
            issues.extend(validation_issues)
        
        is_valid = len(issues) == 0
        
        if not is_valid:
            logger.warning(f"Summary validation failed for {persona}: {', '.join(issues)}")
        
        return is_valid, issues
    
    def _has_business_language(self, summary: str) -> bool:
        """Check if summary uses appropriate business language."""
        business_terms = [
            'functionality', 'feature', 'capability', 'support', 'integration',
            'enhancement', 'improvement', 'implementation', 'solution'
        ]
        summary_lower = summary.lower()
        return any(term in summary_lower for term in business_terms)
    
    def _has_technical_terms(self, summary: str) -> bool:
        """Check if summary includes technical details."""
        technical_patterns = [
            r'\b(class|function|method|API|interface|module|library)\b',
            r'\b(implements?|extends?|inherit|override)\b',
            r'\b(async|await|promise|callback|handler)\b',
            r'\b\w+\(\)',  # Function calls
            r'\b\w+\.\w+',  # Object properties/methods
        ]
        
        for pattern in technical_patterns:
            if re.search(pattern, summary, re.IGNORECASE):
                return True
        return False
    
    def _validate_against_context(
        self, 
        summary: str, 
        code_context: dict,
        persona: str
    ) -> List[str]:
        """Validate summary against actual code changes."""
        issues = []
        
        # Check if mentioned files exist in changes
        file_mentions = re.findall(r'(?:modules?/|src/|lib/|test/)[\w/]+\.\w+', summary)
        if file_mentions and 'file_diffs' in code_context:
            actual_files = {diff.get('filename', '') for diff in code_context['file_diffs']}
            for mentioned_file in file_mentions:
                if mentioned_file not in actual_files:
                    issues.append(f"Mentions non-existent file: {mentioned_file}")
        
        return issues


class SummaryEnhancer:
    """Enhances summaries that fail validation."""
    
    def enhance_summary(
        self,
        original_summary: str,
        validation_issues: List[str],
        persona: str,
        code_context: dict = None
    ) -> str:
        """Attempt to enhance a summary based on validation issues.
        
        Args:
            original_summary: The original summary
            validation_issues: List of validation issues
            persona: The persona type
            code_context: Optional code context
            
        Returns:
            Enhanced summary or original if enhancement fails
        """
        enhanced = original_summary
        
        # Handle specific issues
        for issue in validation_issues:
            if "too short" in issue:
                enhanced = self._expand_summary(enhanced, persona, code_context)
            elif "too long" in issue:
                enhanced = self._condense_summary(enhanced, persona)
            elif "generic content" in issue:
                enhanced = self._make_specific(enhanced, code_context)
        
        return enhanced
    
    def _expand_summary(self, summary: str, persona: str, context: dict) -> str:
        """Expand a summary that's too short."""
        # This is a placeholder - in practice, might need to re-prompt
        return summary
    
    def _condense_summary(self, summary: str, persona: str) -> str:
        """Condense a summary that's too long."""
        # Keep first N sentences based on persona
        sentences = summary.split('. ')
        max_sentences = {"executive": 2, "product": 4, "developer": 6}.get(persona, 4)
        
        if len(sentences) > max_sentences:
            return '. '.join(sentences[:max_sentences]) + '.'
        return summary
    
    def _make_specific(self, summary: str, context: dict) -> str:
        """Make a generic summary more specific."""
        # Remove generic starters
        generic_starters = [
            "This PR ", "This commit ", "These changes ", "The code "
        ]
        
        for starter in generic_starters:
            if summary.startswith(starter):
                summary = summary[len(starter):]
                # Capitalize first letter
                summary = summary[0].upper() + summary[1:] if summary else summary
                break
        
        return summary