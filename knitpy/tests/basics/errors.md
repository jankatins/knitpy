# Errors in code

```python
import NoneExistingModule
```

**ERROR**: ImportError: No module named NoneExistingModule

```
ImportError                               Traceback (most recent call last)
<ipython-input> in <module>()
----> 1 import NoneExistingModule

ImportError: No module named NoneExistingModule
```


```python
raise Exception("Message should be shown...")
```

**ERROR**: Exception: Message should be shown...

```
Exception                                 Traceback (most recent call last)
<ipython-input> in <module>()
----> 1 raise Exception("Message should be shown...")

Exception: Message should be shown...
```


# And both together in one block

```python
import NoneExistingModule
```

**ERROR**: ImportError: No module named NoneExistingModule

```
ImportError                               Traceback (most recent call last)
<ipython-input> in <module>()
----> 1 import NoneExistingModule

ImportError: No module named NoneExistingModule
```

```python
raise Exception("Message should be shown...")
```

**ERROR**: Exception: Message should be shown...

```
Exception                                 Traceback (most recent call last)
<ipython-input> in <module>()
----> 1 raise Exception("Message should be shown...")

Exception: Message should be shown...
```

