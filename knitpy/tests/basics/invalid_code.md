# Invalid Code

```python
"text without a closing quote...
```

**ERROR**: Code invalid


```python
"text without a closing quote...
```

**ERROR**: Code invalid

```python
"More text without a closing quote...
```

**ERROR**: Code invalid


```python
s = ""
# after
   # after2
   print(test)
```

**ERROR**: Code invalid


```python
for i in range(x):

```

**ERROR**: IndentationError: expected an indented block (<ipython-input>, line 2)


```python
for i in range(x):
print(i)
```

**ERROR**: Code invalid