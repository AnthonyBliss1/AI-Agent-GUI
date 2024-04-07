from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('langchain_experimental')
datas = collect_data_files('langchain_experimental')
