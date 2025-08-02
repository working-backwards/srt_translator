"""
CLI Language Manager
Provides command-line utilities for managing and understanding the unified language system
"""

import argparse
import json
import os
import sys
from typing import List, Dict

from .config.language_config import language_config


def list_all_languages():
    """List all available languages"""
    languages = language_config.get_all_languages()
    print(f"\nAvailable Languages ({len(languages)} total):")
    print("=" * 50)
    
    # Sort by popularity first, then by name
    popular_langs = language_config.get_popular_languages()
    
    # Popular languages
    print("\n🌟 Popular Languages:")
    for code in popular_langs:
        if code in languages:
            name = languages[code]['name']
            print(f"  {code:8} - {name}")
    
    # Other languages
    other_langs = [(code, lang['name']) for code, lang in languages.items() 
                   if code not in popular_langs]
    other_langs.sort(key=lambda x: x[1])  # Sort by name
    
    if other_langs:
        print("\n📚 All Languages:")
        for code, name in other_langs:
            print(f"  {code:8} - {name}")


def list_popular_languages():
    """List only popular languages"""
    popular_langs = language_config.get_popular_languages()
    languages = language_config.get_all_languages()
    
    print(f"\n🌟 Popular Languages ({len(popular_langs)}):")
    print("=" * 30)
    
    for code in popular_langs:
        if code in languages:
            name = languages[code]['name']
            print(f"  {code:8} - {name}")


def search_languages(query: str):
    """Search for languages by name or code"""
    languages = language_config.get_all_languages()
    query_lower = query.lower()
    
    matches = []
    for code, lang in languages.items():
        name = lang['name']
        if (query_lower in code.lower() or 
            query_lower in name.lower()):
            matches.append((code, name))
    
    if matches:
        print(f"\n🔍 Search Results for '{query}' ({len(matches)} matches):")
        print("=" * 40)
        for code, name in sorted(matches, key=lambda x: x[1]):
            print(f"  {code:8} - {name}")
    else:
        print(f"\n❌ No languages found matching '{query}'")


def show_language_stats():
    """Show statistics about available languages"""
    languages = language_config.get_all_languages()
    popular_langs = language_config.get_popular_languages()
    
    print("\n📊 Language Statistics:")
    print("=" * 30)
    print(f"Total languages:     {len(languages)}")
    print(f"Popular languages:   {len(popular_langs)}")
    print(f"Other languages:     {len(languages) - len(popular_langs)}")
    print(f"Config version:      {language_config.get_config_version()}")





def show_language_info(code: str):
    """Show detailed information about a specific language"""
    languages = language_config.get_all_languages()
    
    if code not in languages:
        print(f"\n❌ Language code '{code}' not found")
        return
    
    lang = languages[code]
    popular_langs = language_config.get_popular_languages()
    
    print(f"\n📖 Language Information:")
    print("=" * 30)
    print(f"Code:        {code}")
    print(f"Name:        {lang['name']}")
    print(f"Popular:     {'Yes' if lang.get('popular', False) else 'No'}")
    print(f"In Top 12:   {'Yes' if code in popular_langs else 'No'}")
    print(f"Config Ver:  {language_config.get_config_version()}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="SRT Translator Language Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 Examples:
   python -m srt_core.cli_language_manager list-all
   python -m srt_core.cli_language_manager popular
   python -m srt_core.cli_language_manager search spanish
   python -m srt_core.cli_language_manager info es
   python -m srt_core.cli_language_manager stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List all languages
    subparsers.add_parser('list-all', help='List all available languages')
    
    # List popular languages
    subparsers.add_parser('popular', help='List popular languages only')
    
    # Search languages
    search_parser = subparsers.add_parser('search', help='Search for languages')
    search_parser.add_argument('query', help='Search term (language name or code)')
    
    # Show language info
    info_parser = subparsers.add_parser('info', help='Show information about a language')
    info_parser.add_argument('code', help='Language code (e.g., es, fr, de)')
    
    # Show statistics
    subparsers.add_parser('stats', help='Show language statistics')
    

    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'list-all':
            list_all_languages()
        elif args.command == 'popular':
            list_popular_languages()
        elif args.command == 'search':
            search_languages(args.query)
        elif args.command == 'info':
            show_language_info(args.code)
        elif args.command == 'stats':
            show_language_stats()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 