import os
import threading
import requests
from tqdm import tqdm
import time

class Downloader:
    def __init__(self, url, num_threads=1):
        self.url = url
        self.num_threads = min(num_threads, 32)  # 限制最大线程数为32
        self.file_size = 0
        self.download_progress = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.total_progress_bar = tqdm(total=100, desc="总体进度")

    def get_file_size(self):
        response = requests.head(self.url)
        if response.status_code == 200:
            self.file_size = int(response.headers.get('Content-Length', 0))
            print(f"文件大小为: {self.file_size} 字节")

    def download_range(self, start, end, thread_id):
        headers = {'Range': f"bytes={start}-{end}"}
        response = requests.get(self.url, headers=headers, stream=True)
        total_size = end - start + 1

        with open(f"part_{thread_id}", 'wb') as file:
            for chunk in tqdm(response.iter_content(chunk_size=1024), total=total_size//1024, unit="KB", desc=f"线程 {thread_id}"):
                if chunk:
                    file.write(chunk)
                    with self.lock:
                        self.download_progress += len(chunk)
                        total_progress = (self.download_progress / self.file_size) * 100
                        self.total_progress_bar.update(total_progress - self.total_progress_bar.n)

        time_elapsed = time.time() - self.start_time
        download_speed = self.download_progress / time_elapsed if time_elapsed > 0 else 0
        estimated_time_remaining = (self.file_size - self.download_progress) / download_speed if download_speed > 0 else 0

        print(f"线程 {thread_id} 下载完成，用时 {time_elapsed:.2f} 秒，下载速度 {download_speed:.2f} KB/s，预估剩余时间 {estimated_time_remaining:.2f} 秒")

    def merge_files(self, output_filename):
        with open(output_filename, 'wb') as file:
            for i in range(self.num_threads):
                part_file_path = f"part_{i + 1}"
                with open(part_file_path, 'rb') as part_file:
                    file.write(part_file.read())
                # 删除分段文件
                os.remove(part_file_path)

    def download(self):
        self.get_file_size()

        output_filename = input("请输入要保存的文件名（不包含后缀）: ")
        output_filename += input("请输入文件后缀（如 .mp4, .txt 等）: ")

        ranges = [(i * (self.file_size // self.num_threads), (i + 1) * (self.file_size // self.num_threads) - 1) for i in range(self.num_threads)]

        threads = []
        for i, (start, end) in enumerate(ranges):
            thread = threading.Thread(target=self.download_range, args=(start, end, i+1))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.merge_files(output_filename)

        self.total_progress_bar.close()
        print(f"文件下载完成，并保存为 {output_filename}")

if __name__ == "__main__":
    url = input("请输入要下载的URL: ")
    num_threads = int(input("请输入下载线程数 (最好小于32): "))
    
    downloader = Downloader(url, num_threads)
    downloader.download()
