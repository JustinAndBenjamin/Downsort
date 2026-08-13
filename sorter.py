import os
import shutil

def get_readable_size(size_in_bytes):
    """Konvertiert Bytes in eine gut lesbare Größenangabe (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} PB"

def move_file_safely(source_path, target_folder, filename):
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
        
    destination_path = os.path.join(target_folder, filename)
    
    if os.path.exists(destination_path):
        name, extension = os.path.splitext(filename)
        counter = 1
        
        while os.path.exists(destination_path):
            new_filename = f"{name}_{counter:02d}{extension}"
            destination_path = os.path.join(target_folder, new_filename)
            counter += 1

    shutil.move(source_path, destination_path)
    return os.path.basename(destination_path)

def sort_downloads(download_folder, image_folder, document_folder, music_folder, video_folder, application_folder):
    moved_files = []

    for filename in os.listdir(download_folder):
        source_path = os.path.join(download_folder, filename)
        if os.path.isfile(source_path):
            filename_lower = filename.lower()
            
            # Dateigröße ermitteln
            file_size_bytes = os.path.getsize(source_path)
            readable_size = get_readable_size(file_size_bytes)
            
            category = None
            target_folder = None
            
            # 1. Bilder
            if filename_lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg")):
                category = "🖼️  Bilder"
                target_folder = image_folder
                
            # 2. Dokumente
            elif filename_lower.endswith((".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".pptx", ".ppt", ".csv", ".odt")):
                category = "📄 Dokumente"
                target_folder = document_folder
                
            # 3. Reine Audio-Dateien (Musik)
            elif filename_lower.endswith((".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".opus", ".wma", ".alac", ".aiff", ".pcm", ".dsd", ".dff", ".dsf", ".tak", ".tta", ".wv", ".ape", ".spx", ".mpc", ".mpp", ".mka")):
                category = "🎵 Musik"
                target_folder = music_folder
                
            # 4. Reine Video-Dateien
            elif filename_lower.endswith((".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".mpeg", ".mpg", ".webm", ".vob", ".ogv", ".3gp", ".3g2", ".m4v", ".f4v", ".rmvb", ".ts", ".mts", ".m2ts", ".divx", ".xvid", ".asf", ".mpv", ".m2v")):
                category = "🎬 Videos"
                target_folder = video_folder
                
            # 5. Anwendungen & Archive
            elif filename_lower.endswith((".exe", ".msi", ".zip", ".bat", ".rar", ".7z", ".tar", ".gz", ".iso", ".dmg", ".pkg", ".deb", ".rpm", ".appx", ".msix", ".apk", ".jar", ".tgz")):
                category = "⚙️  Anwendungen"
                target_folder = application_folder
            
            if target_folder:
                final_name = move_file_safely(source_path, target_folder, filename)
                moved_files.append({
                    "name": final_name,
                    "category": category,
                    "size": readable_size
                })

    return moved_files