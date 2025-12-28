FNAME="seed.yml"

import yaml

with open(FNAME, "r") as f:
	data = yaml.safe_load(f)

dead_ends = data['dead ends']
areas = data['areas']

tp = data['tp']
all_flags = data['flags']
flags = [key for key in all_flags if all_flags[key]]

toggles = [("CHILD", "ADULT", "SONG_OF_TIME"), ("DAY", "NIGHT", "SUNS_SONG")]

class Route:
	def __init__(self, code, route):
		self.code = code
		self.route = route

	def print(self):
		if self.code == 0:
			print('stay put')
			return
		if self.code == -1:
			print('no path found!')
			return

		for i in range(0, len(self.route) - 1, 2):
			print(self.route[i], "=>", self.route[i+1])
		print(self.route[-1])

class PathTable:
	class TableEntry:
		def __init__(self, path, dist):
			self.path = path
			self.dist = dist

	def __init__(self, areas, dead_ends, tp, toggles, flags):
		self.areas = areas
		self.areas = [(key, list(area[key].items())) for area in areas for key in area]
		self.areas += [(dead_end, []) for dead_end in dead_ends]

		self.n = len(self.areas)
		self.k = self.n - len(dead_ends)

		for warp in tp:
			if tp[warp] is None:
				continue
			for i in range(self.k):
				self.areas[i][1].append((warp, tp[warp]))

		self.rl = {}
		for i in range(self.n):
			self.rl[self.areas[i][0]] = i

		self.toggles = toggles

		flag_combos = [[]]

		index = 1
		for toggle in toggles:
			a, b, change_ability = toggle
			if change_ability in flags:
				flags += [a, b]
				continue
			flag_combos *= 2
			for i in range(index):
				flag_combos[i] = [*flag_combos[i], a]
			for i in range(index, len(flag_combos)):
				flag_combos[i] = [*flag_combos[i], b]
			index *= 2

		self.flag_combos = flag_combos
		self.base_table = self.generate_paths(flags, True)

		self.tables = []

		for flag_combo in flag_combos:
			self.tables.append(self.generate_paths([*flags, *flag_combo], False))

	def dist(self, flags_index, start, end):
		return self.tables[flags_index][self.rl[start]][self.rl[end]].dist

	def dump(self, area_id):
		area = self.areas[self.rl[area_id]]
		exits = area[1]
		for e in exits:
			print(e[0], '--->', e[1])

	def generate_paths(self, flags, base):
		def empty_table(k, n):
			table = [[None] * n for _ in range(k)] 
			for i in range(k):
				for j in range(n):
					table[i][j] = self.TableEntry(None, None)
			return table

		def copy_base_table():
			table = [[self.TableEntry(cell.path, cell.dist) for cell in row] for row in self.base_table]
			return table

		table = empty_table(self.k, self.n) if base else copy_base_table()

		for i in range(self.k):
			area = self.areas[i]
			name = area[0]
			exits = area[1]

			for e in exits:
				exit_name = e[0]
				exit_loc = e[1]
				if exit_loc is None:
					continue

				cond_start = exit_name.find('<')
				cond_end = exit_name.find('>')

				if (base or cond_start != -1):
					conditions = exit_name[cond_start+1:cond_end].split() 
					meets_conditions = True
					for condition in conditions:
						if condition not in flags:
							meets_conditions = False
							break
					if not meets_conditions:
						continue

				table[i][self.rl[exit_loc]] = self.TableEntry(e[0], 1)

		for i in range(self.k):
			table[i][i].dist = 0
			
		def loop():
			done = True
			for start in range(self.k):
				for end in range(self.n):
					dist_start_end = table[start][end].dist
					if dist_start_end is None:
						continue
					for area in range(self.k):
						if table[area][start].dist is None:
							continue
						dist_area_start = table[area][start].dist
						if (dist_area_start != 1):
							continue
						dist_area_end = table[area][end].dist
						dist_via_start = dist_area_start + dist_start_end
						if dist_area_end is None or dist_via_start < dist_area_end:
							table[area][end] = self.TableEntry(start, dist_via_start)
							done = False
			return done

		while not loop():
			continue

		return table

	def find_route(self, flags_index, start, end):
		flags = self.flag_combos[flags_index]
		s = self.rl[start]
		e = self.rl[end]

		table = self.tables[flags_index]
		path = table[s][e].path
		dist = table[s][e].dist

		if dist == 0:
			return Route(0, None)

		if path is None:
			return Route(-1, None)

		if dist == 1:
			return Route(s * self.k + e, [start, path, end])

		route = self.find_route(flags_index, self.areas[path][0], end)
		return Route(route.code * self.k + s, [start, table[s][path].path] + route.route)

	def find_routes(self, start, end):
		n = len(self.tables)

		codes = [None] * n
		routes = {}

		for i in range(n):
			flags = self.flag_combos[i]
			dist = self.dist(i, start, end)

			route = self.find_route(i, start, end)
			codes[i] = route.code
			if route.code not in routes:
				routes[route.code] = route

		sep = '\n------------------------------\n'
		routes_shown = []

		flag_combos = [None] * n
		for i in range(n):
			this_flagset = [*self.flag_combos[i]]
			for j in range(i):
				if codes[i] == codes[j]:
					that_flagset = flag_combos[j]
					for k in range(len(this_flagset)):
						if this_flagset[k] != that_flagset[k]:
							this_flagset[k] = None
							that_flagset[k] = None
			flag_combos[i] = this_flagset
		for i in range(n):
			flag_combos[i] = [flag for flag in flag_combos[i] if flag is not None]

		for i in range(n):
			code = codes[i]
			if code not in routes_shown and code is not None:
				conditions = flag_combos[i]
				parentheses = '(%s)' % ', '.join(conditions) if len(conditions) > 0 else ''
				print(sep, parentheses)
				routes[code].print()
				routes_shown.append(code)


path_table = PathTable(areas, dead_ends, tp, toggles, flags)

start = input('from: ')
if start not in path_table.rl:
	print('unknown area "%s"' % start)
	exit()

end = input('to:   ')
if end not in path_table.rl and end not in ['dump']:
	print('unknown area "%s"' % end)
	exit()

if (end == 'dump'):
	path_table.dump(start)
else:
	path_table.find_routes(start, end)

blank_data = {
	"tp": { key: None for key in tp },
	"flags": { key: False for key in all_flags },
	"dead ends": dead_ends,
	"areas": [{area[0]: {path[0]: None for path in area[1] if path[0] not in tp}} for area in path_table.areas[:path_table.k]]
}

## little kludge to represent None as empty string in yaml output
def represent_none(self, _):
    return self.represent_scalar('tag:yaml.org,2002:null', '')

yaml.add_representer(type(None), represent_none)
yaml.representer.SafeRepresenter.add_representer(type(None), represent_none)
yaml.SafeDumper.add_representer(type(None), lambda self, data: self.represent_scalar("tag:yaml.org,2002:null", ""))
###

with open("newseed.yml", "w") as f:
	yaml.dump(blank_data, f, sort_keys=False)
