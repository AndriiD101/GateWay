for remote in $(git branch -r | grep -v '\->'); do
    git checkout --track $remote
done
