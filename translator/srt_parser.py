# translator/srt_parser.py

class SRTParser:
    @staticmethod
    def parse_file(filepath):
        """Parse an SRT file into a list of subtitle entries"""
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
        
        subtitle_blocks = content.strip().split('\n\n')
        parsed_subtitles = []
        
        for block in subtitle_blocks:
            lines = block.split('\n')
            
            if len(lines) < 3:
                continue
            
            subtitle_number = lines[0]
            timestamp = lines[1]
            subtitle_text = ' '.join(lines[2:])
            
            parsed_subtitles.append({
                'number': subtitle_number,
                'timestamp': timestamp,
                'text': subtitle_text
            })
        
        return parsed_subtitles

    @staticmethod
    def write_file(filepath, subtitles):
        """Write subtitles to an SRT file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as file:
            for subtitle in subtitles:
                file.write(f"{subtitle['number']}\n")
                file.write(f"{subtitle['timestamp']}\n")
                file.write(f"{subtitle['translated_text']}\n\n")