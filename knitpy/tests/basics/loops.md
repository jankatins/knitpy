# Loops

Problem here is that the loop + the first line is usually enough to make something valid code

```python
s = ""
for i in range(10):
    s += " %s" %i
s
```

```
## ' 0 1 2 3 4 5 6 7 8 9'
```

```python
s = ""
for i in range(10):
    j = i
    s += " %s" %j
s
```

```
## ' 0 1 2 3 4 5 6 7 8 9'
```

```python
s = ""
for i in range(10):
   # test
    j = i
    # test
# test
    # test
    s += " %s" %j
s
```

```
## ' 0 1 2 3 4 5 6 7 8 9'
```

```python
s = ""
for i in range(10):
    for j in range(i):
        s += " %s" %j
s
```

```
## ' 0 0 1 0 1 2 0 1 2 3 0 1 2 3 4 0 1 2 3 4 5 0 1 2 3 4 5 6 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 8'
```

```python
s = ""
for i in range(10):
    for j in range(i):
        k = j
        s += " %s" %k
s
```

```
## ' 0 0 1 0 1 2 0 1 2 3 0 1 2 3 4 0 1 2 3 4 5 0 1 2 3 4 5 6 0 1 2 3 4 5 6 7 0 1 2 3 4 5 6 7 8'
```

```python
s = ""
for i in range(10):
    for j in range(i):
        k = j
        s += " %s" %k
    s += " loop"
s
```

```
## ' loop 0 loop 0 1 loop 0 1 2 loop 0 1 2 3 loop 0 1 2 3 4 loop 0 1 2 3 4 5 loop 0 1 2 3 4 5 6 loop 0 1 2 3 4 5 6 7 loop 0 1 2 3 4 5 6 7 8 loop'
```

```python
 # test
for i in range(3):
    # test
      #test
    print(i)
# text
    print("works")
```

```
## 0
## works
## 1
## works
## 2
## works
```
