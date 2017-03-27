
unittest:
	chmod a+rwx `pwd`
	python dcube.py --file `pwd`/data/toyexample.csv --measure_attr 2 --density_type 'ari' --selection_policy 'cardinality' --num_dense_blocks 3
	python dcube.py --file `pwd`/data/toyexample.csv --measure_attr 2 --density_type 'geo' --selection_policy 'cardinality' --num_dense_blocks 3
	python dcube.py --file `pwd`/data/toyexample.csv --measure_attr 2 --density_type 'susp' --selection_policy 'cardinality' --num_dense_blocks 3
	python dcube.py --file `pwd`/data/toyexample.csv --measure_attr 2 --density_type 'ari' --selection_policy 'density' --num_dense_blocks 3
	python dcube.py --file `pwd`/data/toyexample.csv --measure_attr 2 --density_type 'geo' --selection_policy 'density' --num_dense_blocks 3
	python dcube.py --file `pwd`/data/toyexample.csv --measure_attr 2 --density_type 'susp' --selection_policy 'density' --num_dense_blocks 3
	python dcube.py --file `pwd`/data/toysample.csv --measure_attr 3 --density_type 'ari' --selection_policy 'density' --num_dense_blocks 1
	python dcube.py --file `pwd`/data/toysample.csv --measure_attr 3 --density_type 'geo' --selection_policy 'cardinality' --num_dense_blocks 1

darpa:
	chmod a+rwx `pwd`
	wget http://www.cs.cmu.edu/~christos/courses/826-resources/DATA-SETS-graphs/datasets/darpa.csv
	mkdir -p data
	mv darpa.csv data/
	python -u dcube.py --file `pwd`/data/darpa.csv --colname 'source_ip destination_id time_in_minutes' --density_type 'ari' --selection_policy 'cardinality' --num_dense_blocks 1 > ari_cardinality
	python -u dcube.py --file `pwd`/data/darpa.csv --colname 'source_ip destination_id time_in_minutes' --density_type 'geo' --selection_policy 'cardinality' --num_dense_blocks 1 > geo_cardinality
	python -u dcube.py --file `pwd`/data/darpa.csv --colname 'source_ip destination_id time_in_minutes' --density_type 'susp' --selection_policy 'cardinality' --num_dense_blocks 1 > susp_cardinality
	python -u dcube.py --file `pwd`/data/darpa.csv --colname 'source_ip destination_id time_in_minutes' --density_type 'ari' --selection_policy 'density' --num_dense_blocks 1 > ari_density
	python -u dcube.py --file `pwd`/data/darpa.csv --colname 'source_ip destination_id time_in_minutes' --density_type 'geo' --selection_policy 'density' --num_dense_blocks 1 > geo_density
	python -u dcube.py --file `pwd`/data/darpa.csv --colname 'source_ip destination_id time_in_minutes' --density_type 'susp' --selection_policy 'density' --num_dense_blocks 1 > susp_density
	



