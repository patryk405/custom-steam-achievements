"""Small native setup window. Writes overrides, never touches game files."""
import json
import os
from pathlib import Path
from cloud import write, read

FILES = {'botw':'botw','oot':'oot','bloodborne':'bbport','arceus':'arceus','odyssey':'odyssey','pokopia':'pokopia'}

def save_configuration(root, data, game, selected, title_id=''):
    manifest = json.loads((root/'resources'/f'{FILES[game]}-adapter.json').read_text())
    path = Path(selected).expanduser().resolve(strict=True)
    if game == 'oot':
        if os.name == 'nt': raise ValueError('Longshot live tracking currently requires Linux.')
        manifest['socket'] = str(path)
    elif game == 'bloodborne':
        import re
        if not path.is_dir(): raise ValueError('Select the BBPort user directory.')
        if not re.fullmatch(r'CUSA\d{5}', title_id): raise ValueError('Enter the CUSA title ID, for example CUSA00900.')
        manifest.update(root=str(path),titleId=title_id)
    else:
        if not path.is_file(): raise ValueError('Select a save file, not a directory.')
        manifest.update(root=str(path.parent),glob=path.name)
        # Explicitly choosing saves must work without any live launch wrapper.
        if game == 'pokopia': manifest.update(liveOnly=False)
    write(data/'adapters'/f'{FILES[game]}-adapter.json', manifest)

def configure(root, data):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    catalog = json.loads((root/'resources/catalog.json').read_text())
    app = tk.Tk(); app.title('Custom Steam Achievements — Game setup'); app.geometry('660x310')
    frame = ttk.Frame(app,padding=20); frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Select your game and its progress file.').pack(anchor='w')
    choices = list(FILES); names = [catalog[g]['name'] for g in choices]
    game = ttk.Combobox(frame,values=names,state='readonly'); game.current(0); game.pack(fill='x',pady=10)
    selected = tk.StringVar(); ttk.Entry(frame,textvariable=selected).pack(fill='x')
    def browse():
        value = filedialog.askdirectory() if choices[game.current()] == 'bloodborne' else filedialog.askopenfilename()
        if value: selected.set(value)
    ttk.Button(frame,text='Choose save file / BBPort directory',command=browse).pack(anchor='w',pady=6)
    ttk.Label(frame,text='BOTW: game_data.sav · Arceus: main · Odyssey: File1.bin\nPokopia: CMNDAT.BIN · Ocarina: Longshot control socket').pack(anchor='w')
    row=ttk.Frame(frame);row.pack(fill='x',pady=8)
    ttk.Label(row,text='Bloodborne title ID (only for BBPort): ').pack(side='left')
    title=tk.StringVar();ttk.Entry(row,textvariable=title,width=15).pack(side='left')
    def save():
        try:
            save_configuration(root,data,choices[game.current()],selected.get(),title.get().strip())
            messagebox.showinfo('Saved','Settings saved. Open this game in your Steam library once to connect notifications. The tracker reloads settings automatically.')
        except Exception as error: messagebox.showerror('Could not save',str(error))
    ttk.Button(frame,text='Save settings',command=save).pack(anchor='e')
    app.mainloop()
